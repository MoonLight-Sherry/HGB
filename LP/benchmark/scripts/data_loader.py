import os
import numpy as np
import scipy.sparse as sp
from collections import Counter, defaultdict
from sklearn.metrics import f1_score, auc, roc_auc_score, precision_recall_curve
import random


class data_loader:
    def __init__(self, path, random_test=False):
        self.path = path
        self.nodes = self.load_nodes()
        self.links = self.load_links('link.dat')
        self.links_test = self.load_links('link.dat.test')
        if random_test:
            self.test_neigh = self.get_test_neigh_w_random()
        else:
            self.test_neigh = self.get_test_neigh()
        self.types = self.load_types('node.dat')

    def get_sub_graph(self, node_types_tokeep):
        """
        node_types_tokeep is a list or set of node types that you want to keep in the sub-graph
        We only support whole type sub-graph for now.
        This is an in-place update function!
        return: old node type id to new node type id dict, old edge type id to new edge type id dict
        """
        keep = set(node_types_tokeep)
        new_node_type = 0
        new_node_id = 0
        new_nodes = {'total': 0, 'count': Counter(), 'attr': {}, 'shift': {}}
        new_links = {'total': 0, 'count': Counter(), 'meta': {}, 'data': defaultdict(list)}
        new_labels_train = {'num_classes': 0, 'total': 0, 'count': Counter(), 'data': None, 'mask': None}
        new_labels_test = {'num_classes': 0, 'total': 0, 'count': Counter(), 'data': None, 'mask': None}
        old_nt2new_nt = {}
        old_idx = []
        for node_type in self.nodes['count']:
            if node_type in keep:
                nt = node_type
                nnt = new_node_type
                old_nt2new_nt[nt] = nnt
                cnt = self.nodes['count'][nt]
                new_nodes['total'] += cnt
                new_nodes['count'][nnt] = cnt
                new_nodes['attr'][nnt] = self.nodes['attr'][nt]
                new_nodes['shift'][nnt] = new_node_id
                beg = self.nodes['shift'][nt]
                old_idx.extend(range(beg, beg + cnt))

                cnt_label_train = self.labels_train['count'][nt]
                new_labels_train['count'][nnt] = cnt_label_train
                new_labels_train['total'] += cnt_label_train
                cnt_label_test = self.labels_test['count'][nt]
                new_labels_test['count'][nnt] = cnt_label_test
                new_labels_test['total'] += cnt_label_test

                new_node_type += 1
                new_node_id += cnt

        new_labels_train['num_classes'] = self.labels_train['num_classes']
        new_labels_test['num_classes'] = self.labels_test['num_classes']
        for k in ['data', 'mask']:
            new_labels_train[k] = self.labels_train[k][old_idx]
            new_labels_test[k] = self.labels_test[k][old_idx]

        old_et2new_et = {}
        new_edge_type = 0
        for edge_type in self.links['count']:
            h, t = self.links['meta'][edge_type]
            if h in keep and t in keep:
                et = edge_type
                net = new_edge_type
                old_et2new_et[et] = net
                new_links['total'] += self.links['count'][et]
                new_links['count'][net] = self.links['count'][et]
                new_links['meta'][net] = tuple(map(lambda x: old_nt2new_nt[x], self.links['meta'][et]))
                new_links['data'][net] = self.links['data'][et][old_idx][:, old_idx]
                new_edge_type += 1

        self.nodes = new_nodes
        self.links = new_links
        self.labels_train = new_labels_train
        self.labels_test = new_labels_test
        return old_nt2new_nt, old_et2new_et

    def get_meta_path(self, meta=[]):
        """
        Get meta path matrix
            meta is a list of edge types (also can be denoted by a pair of node types)
            return a sparse matrix with shape [node_num, node_num]
        """
        ini = sp.eye(self.nodes['total'])
        meta = [self.get_edge_type(x) for x in meta]
        for x in meta:
            ini = ini.dot(self.links['data'][x]) if x >= 0 else ini.dot(self.links['data'][-x - 1].T)
        return ini

    def dfs(self, now, meta, meta_dict):
        if len(meta) == 0:
            meta_dict[now[0]].append(now)
            return
        th_mat = self.links['data'][meta[0]] if meta[0] >= 0 else self.links['data'][-meta[0] - 1].T
        th_node = now[-1]
        for col in th_mat[th_node].nonzero()[1]:
            self.dfs(now + [col], meta[1:], meta_dict)

    def get_full_meta_path(self, meta=[]):
        """
        Get full meta path for each node
            meta is a list of edge types (also can be denoted by a pair of node types)
            return a dict of list[list] (key is node_id)
        """
        meta = [self.get_edge_type(x) for x in meta]
        if len(meta) == 1:
            meta_dict = {}
            for i in range(self.nodes['total']):
                meta_dict[i] = []
                self.dfs([i], meta, meta_dict)
        else:
            meta_dict1 = {}
            meta_dict2 = {}
            mid = len(meta) // 2
            meta1 = meta[:mid]
            meta2 = meta[mid:]
            for i in range(self.nodes['total']):
                meta_dict1[i] = []
                self.dfs([i], meta1, meta_dict1)
            for i in range(self.nodes['total']):
                meta_dict2[i] = []
                self.dfs([i], meta2, meta_dict2)
            meta_dict = {}
            for i in range(self.nodes['total']):
                meta_dict[i] = []
                for beg in meta_dict1[i]:
                    for end in meta_dict2[beg[-1]]:
                        meta_dict[i].append(beg + end[1:])
        return meta_dict

    def evaluate(self, edge_list, confidence, labels, threshold=0.5):
        """
        :param edge_list: shape(2, edge_num)
        :param confidence: shape(1, edge_num)
        :param labels: shape(1, edge_num)
        :param threshold: label of confidence in range(0,threshold) is 0 else 1
        :return: dict with all scores we need
        """
        confidence = np.array(confidence)
        labels = np.array(labels)
        labels_pred = np.zeros(np.shape(confidence)[0])
        labels_pred[np.where(confidence >= threshold)] = 1
        ps, rs, _ = precision_recall_curve(labels, confidence)
        auc_socre = auc(rs, ps)
        roc_auc = roc_auc_score(labels, confidence)
        f1 = f1_score(labels, labels_pred)

        mrr_list, cur_mrr = [], 0
        t_dict, labels_dict, conf_dict = defaultdict(list), defaultdict(list), defaultdict(list)
        for i, h_id in enumerate(edge_list[0]):
            t_dict[h_id].append(edge_list[1][i])
            labels_dict[h_id].append(labels[i])
            conf_dict[h_id].append(confidence[i])
        for h_id in t_dict.keys():
            conf_array = np.array(conf_dict[h_id])
            rank = np.argsort(-conf_array)
            sorted_label_array = np.array(labels_dict[h_id])[rank]
            pos_index = np.where(sorted_label_array == 1)[0]
            pos_min_rank = np.min(pos_index)
            cur_mrr = 1 / (1 + pos_min_rank)
            mrr_list.append(cur_mrr)
        return {'auc_score': auc_socre, 'roc_auc': roc_auc, 'F1': f1, 'MRR': np.mean(mrr_list)}

    def get_node_type(self, node_id):
        for i in range(len(self.nodes['shift'])):
            if node_id < self.nodes['shift'][i] + self.nodes['count'][i]:
                return i

    def get_edge_type(self, info):
        if type(info) is int or len(info) == 1:
            return info
        for i in range(len(self.links['meta'])):
            if self.links['meta'][i] == info:
                return i
        info = (info[1], info[0])
        for i in range(len(self.links['meta'])):
            if self.links['meta'][i] == info:
                return -i - 1
        raise Exception('No available edge type')

    def get_edge_info(self, edge_id):
        return self.links['meta'][edge_id]

    def list_to_sp_mat(self, li):
        data = [x[2] for x in li]
        i = [x[0] for x in li]
        j = [x[1] for x in li]
        return sp.coo_matrix((data, (i, j)), shape=(self.nodes['total'], self.nodes['total'])).tocsr()

    def load_types(self, name):
        """
        return types dict
            types: list of types
            total: total number of nodes
            data: a dictionary of type of all nodes)
        """
        types = {'types': list(), 'total': 0, 'data': dict()}
        with open(os.path.join(self.path, name), 'r', encoding='utf-8') as f:
            for line in f:
                th = line.strip().split('\t')
                node_id, node_name, node_type = int(th[0]), th[1], int(th[2])
                types['data'][node_id] = node_type
                types['types'].append(node_type)
                types['total'] += 1
        types['types'] = list(set(types['types']))
        return types

    def get_train_neg_neigh(self):
        neg_neigh = dict()
        for r_id in self.links['data'].keys():
            h_type, t_type = self.links['meta'][r_id]
            t_range = (self.nodes['shift'][t_type], self.nodes['shift'][t_type] + self.nodes['count'][t_type])
            '''get neg_neigh'''
            neg_neigh[r_id] = defaultdict(list)
            (row, col), data = self.links['data'][r_id].nonzero(), self.links['data'][r_id].data
            for h_id, t_id in zip(row, col):
                neg_t = int(random.random() * (t_range[1] - t_range[0])) + t_range[0]
                neg_neigh[r_id][h_id].append(neg_t)
        return neg_neigh

    def get_test_neigh(self):
        neg_neigh, pos_neigh, test_neigh = dict(), dict(), dict()
        '''get sec_neigh'''
        pos_links = 0
        for r_id in self.links['data'].keys():
            pos_links += self.links['data'][r_id] + self.links['data'][r_id].T
        for r_id in self.links_test['data'].keys():
            pos_links += self.links_test['data'][r_id] + self.links_test['data'][r_id].T
        r_double_neighs = np.dot(pos_links, pos_links)
        data = r_double_neighs.data
        data[:] = 1
        r_double_neighs = \
            sp.coo_matrix((data, r_double_neighs.nonzero()), shape=np.shape(pos_links), dtype=int) \
            - sp.coo_matrix(pos_links, dtype=int) \
            - sp.lil_matrix(np.eye(np.shape(pos_links)[0], dtype=int))

        row, col = r_double_neighs.nonzero()
        data = r_double_neighs.data
        sec_index = np.where(data > 0)
        row, col = row[sec_index], col[sec_index]

        relation_range = [self.nodes['shift'][k] for k in range(len(self.nodes['shift']))] + [self.nodes['total']]
        for r_id in self.links_test['data'].keys():
            neg_neigh[r_id] = defaultdict(list)
            h_type, t_type = self.links_test['meta'][r_id]
            r_id_index = np.where((row >= relation_range[h_type]) & (row < relation_range[h_type + 1])
                                  & (col >= relation_range[t_type]) & (col < relation_range[t_type + 1]))[0]
            # r_num = np.zeros((3, 3))
            # for h_id, t_id in zip(row, col):
            #     r_num[self.get_node_type(h_id)][self.get_node_type(t_id)] += 1
            r_row, r_col = row[r_id_index], col[r_id_index]
            for h_id, t_id in zip(r_row, r_col):
                neg_neigh[r_id][h_id].append(t_id)

        for r_id in self.links_test['data'].keys():
            '''get pos_neigh'''
            pos_neigh[r_id] = defaultdict(list)
            (row, col), data = self.links_test['data'][r_id].nonzero(), self.links_test['data'][r_id].data
            for h_id, t_id in zip(row, col):
                pos_neigh[r_id][h_id].append(t_id)

            '''sample neg as same number as pos for each head node'''
            test_neigh[r_id] = defaultdict(list)
            for h_id in pos_neigh[r_id].keys():
                pos_list = pos_neigh[r_id][h_id]
                random.seed(1)
                neg_list = random.choices(neg_neigh[r_id][h_id], k=len(pos_list))
                test_neigh[r_id][h_id] = pos_list + neg_list
        return test_neigh

    def get_test_neigh_w_random(self):
        neg_neigh, pos_neigh, test_neigh = dict(), dict(), dict()

        for r_id in self.links_test['data'].keys():
            h_type, t_type = self.links_test['meta'][r_id]
            t_range = (self.nodes['shift'][t_type], self.nodes['shift'][t_type] + self.nodes['count'][t_type])
            '''get pos_neigh and neg_neigh'''
            pos_neigh[r_id], neg_neigh[r_id] = defaultdict(list), defaultdict(list)
            (row, col), data = self.links_test['data'][r_id].nonzero(), self.links_test['data'][r_id].data
            for h_id, t_id in zip(row, col):
                pos_neigh[r_id][h_id].append(t_id)
                random.seed(1)
                neg_t = int(random.random() * (t_range[1] - t_range[0])) + t_range[0]
                neg_neigh[r_id][h_id].append(neg_t)

            '''get the test_neigh'''
            test_neigh[r_id] = defaultdict(list)
            for h_id in pos_neigh[r_id].keys():
                pos_list = pos_neigh[r_id][h_id]
                neg_list = neg_neigh[r_id][h_id]
                test_neigh[r_id][h_id] = pos_list + neg_list
        return test_neigh

    def load_links(self, name):
        """
        return links dict
            total: total number of links
            count: a dict of int, number of links for each type
            meta: a dict of tuple, explaining the link type is from what type of node to what type of node
            data: a dict of sparse matrices, each link type with one matrix. Shapes are all (nodes['total', nodes['total'])
        """
        links = {'total': 0, 'count': Counter(), 'meta': {}, 'data': defaultdict(list)}
        with open(os.path.join(self.path, name), 'r', encoding='utf-8') as f:
            for line in f:
                th = line.split('\t')
                h_id, t_id, r_id, link_weight = int(th[0]), int(th[1]), int(th[2]), float(th[3])
                if r_id not in links['meta']:
                    h_type = self.get_node_type(h_id)
                    t_type = self.get_node_type(t_id)
                    links['meta'][r_id] = (h_type, t_type)
                links['data'][r_id].append((h_id, t_id, link_weight))
                links['count'][r_id] += 1
                links['total'] += 1
        new_data = {}
        for r_id in links['data']:
            new_data[r_id] = self.list_to_sp_mat(links['data'][r_id])
        links['data'] = new_data
        return links

    def load_nodes(self):
        """
        return nodes dict
            total: total number of nodes
            count: a dict of int, number of nodes for each type
            attr: a dict of np.array (or None), attribute matrices for each type of nodes
            shift: node_id shift for each type. You can get the id range of a type by 
                        [ shift[node_type], shift[node_type]+count[node_type] )
        """
        nodes = {'total': 0, 'count': Counter(), 'attr': {}, 'shift': {}}
        with open(os.path.join(self.path, 'node.dat'), 'r', encoding='utf-8') as f:
            for line in f:
                th = line.split('\t')
                if len(th) == 4:
                    # Then this line of node has attribute
                    node_id, node_name, node_type, node_attr = th
                    node_id = int(node_id)
                    node_type = int(node_type)
                    node_attr = list(map(float, node_attr.split(',')))
                    nodes['count'][node_type] += 1
                    nodes['attr'][node_id] = node_attr
                    nodes['total'] += 1
                elif len(th) == 3:
                    # Then this line of node doesn't have attribute
                    node_id, node_name, node_type = th
                    node_id = int(node_id)
                    node_type = int(node_type)
                    nodes['count'][node_type] += 1
                    nodes['total'] += 1
                else:
                    raise Exception("Too few information to parse!")
        shift = 0
        attr = {}
        for i in range(len(nodes['count'])):
            nodes['shift'][i] = shift
            if shift in nodes['attr']:
                mat = []
                for j in range(shift, shift + nodes['count'][i]):
                    mat.append(nodes['attr'][j])
                attr[i] = np.array(mat)
            else:
                attr[i] = None
            shift += nodes['count'][i]
        nodes['attr'] = attr
        return nodes

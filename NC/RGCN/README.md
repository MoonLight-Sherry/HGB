# RGCN code

Adapted from [DGL example](https://github.com/dmlc/dgl/tree/master/examples/pytorch/rgcn).

We replace the GNN module in paper by GCN for comparison.

## running environment

## running procedure
* Python 3.7
* torch 1.7.0
* dgl 0.5.2

* Dataset will be downloaded automatically at ~/.dgl/.
* or you can download data from [tsinghua-cloud](https://cloud.tsinghua.edu.cn/d/8b9644cfa8344f26878c/) or [google-drive](https://drive.google.com/drive/folders/13o5dYuvpZWzgeUPVTLLtpYHAGss2sk_x?usp=sharing)
* unzip all zip files
* move them to ~/.dgl/
* cd to RGCN/
* run python file

```bash
python3 entity_classify.py -d aifb --gpu=0 --lr=0.001 --model=gcn
python3 entity_classify.py -d mutag --l2norm 1e-2 --gpu=0 --lr=0.01 --n-hidden=32 --model=gcn
python3 entity_classify.py -d bgs --gpu=0 --n-hidden=64  --lr=0.05 --model=gcn
python3 entity_classify.py -d am --n-hidden=64 --gpu=0 --lr=0.01  --model=gcn

python3 entity_classify.py -d aifb --gpu=0 --lr=0.002 --model=gat
python3 entity_classify.py -d mutag  --gpu=0 --lr=0.008 --n-hidden=32 --dropout=0.5 --l2norm=5e-3 --model=gat
python3 entity_classify.py -d bgs --gpu=0 --n-hidden=32 --l2norm=5e-4  --lr=0.01 --model=gat --dropout=0.4
python3 entity_classify.py -d am --n-hidden=64 --gpu=0 --lr=0.01  --model=gat --dropout=0.3

python3 entity_classify.py -d aifb --gpu=0
python3 entity_classify.py -d mutag --l2norm 5e-4 --n-bases 30 --gpu=0
python3 entity_classify.py -d bgs --l2norm 5e-4 --n-bases 40  --gpu=0
python3 entity_classify.py -d am --n-bases=40 --n-hidden=10 --l2norm=5e-4 --gpu=0
```
## performance report

|               | AIFB  | MUTAG |  BGS  |  AM   |
| :-----------: | :---: | :---: | :---: | :---: |
|      GCN      | 97.22 | 73.82 | 86.21 | 81.92 |
|      GAT      |       | 72.65 | 86.21 |       |
|     RGCN      | 95.83 | 73.23 | 83.1  | 90.4  |
| RGCN on paper | 92.59 | 70.1  | 88.51 | 89.29 |


***The following content is from the initial hwwang55/KGCN repo.***
# Relational-GCN

* Paper: [https://arxiv.org/abs/1703.06103](https://arxiv.org/abs/1703.06103)
* Author's code for entity classification: [https://github.com/tkipf/relational-gcn](https://github.com/tkipf/relational-gcn)
* Author's code for link prediction: [https://github.com/MichSchli/RelationPrediction](https://github.com/MichSchli/RelationPrediction)

### Dependencies
* PyTorch 0.4.1+
* requests
* rdflib
* pandas

```
pip install requests torch rdflib pandas
```

Example code was tested with rdflib 4.2.2 and pandas 0.23.4

### Entity Classification
AIFB: accuracy 92.59% (3 runs, DGL), 95.83% (paper)
```
python3 entity_classify.py -d aifb --testing --gpu 0
```

MUTAG: accuracy 72.55% (3 runs, DGL), 73.23% (paper)
```
python3 entity_classify.py -d mutag --l2norm 5e-4 --n-bases 30 --testing --gpu 0
```

BGS: accuracy 89.66% (3 runs, DGL), 83.10% (paper)
```
python3 entity_classify.py -d bgs --l2norm 5e-4 --n-bases 40 --testing --gpu 0
```

AM: accuracy 89.73% (3 runs, DGL), 89.29% (paper)
```
python3 entity_classify.py -d am --n-bases=40 --n-hidden=10 --l2norm=5e-4 --testing
```

### Entity Classification with minibatch
AIFB: accuracy avg(5 runs) 90.56%, best 94.44% (DGL)
```
python3 entity_classify_mp.py -d aifb --testing --gpu 0 --fanout='20,20' --batch-size 128
```

MUTAG: accuracy avg(5 runs) 66.77%, best 69.12% (DGL)
```
python3 entity_classify_mp.py -d mutag --l2norm 5e-4 --n-bases 30 --testing --gpu 0 --batch-size 256 --use-self-loop --n-epochs 40
```

BGS: accuracy avg(5 runs) 91.72%, best 96.55% (DGL)
```
python3 entity_classify_mp.py -d bgs --l2norm 5e-4 --n-bases 40 --testing --gpu 0 --fanout '40,40' --n-epochs=40 --batch-size=128
```

AM: accuracy avg(5 runs) 88.28%, best 90.40% (DGL)
```
python3 entity_classify_mp.py -d am --l2norm 5e-4 --n-bases 40 --testing --gpu 0 --fanout '35,35' --batch-size 256 --lr 1e-2 --n-hidden 16 --use-self-loop --n-epochs=40
```

### Entity Classification on OGBN-MAG
Test-bd: P3-8xlarge

OGBN-MAG accuracy 46.22
```
python3 entity_classify_mp.py -d ogbn-mag --testing --fanout='25,30' --batch-size 512 --n-hidden 64 --lr 0.01 --num-worker 0 --eval-batch-size 8 --low-mem --gpu 0,1,2,3,4,5,6,7 --dropout 0.5 --use-self-loop --n-bases 2 --n-epochs 3 --mix-cpu-gpu --node-feats
```

OGBN-MAG without node-feats 43.63
```
python3 entity_classify_mp.py -d ogbn-mag --testing --fanout='25,25' --batch-size 256 --n-hidden 64 --lr 0.01 --num-worker 0 --eval-batch-size 8 --low-mem --gpu 0,1,2,3,4,5,6,7 --dropout 0.5 --use-self-loop --n-bases 2 --n-epochs 3 --mix-cpu-gpu --layer-norm
```

Test-bd: P2-8xlarge
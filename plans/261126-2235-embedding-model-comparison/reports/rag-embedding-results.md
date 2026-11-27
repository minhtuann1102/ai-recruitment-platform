# RAG: so sanh model embedding (2026-11-27)

git HEAD d6b1079d1f; corpus 8356 chunk interview_qa (4178 qa_id; {'qa_pair': 4178, 'question': 4178}), vector 3-small doc tu ai_db. Mot duong tim cho moi model: cosine toan kho -> k*OVERFETCH(4) -> dedup qa_id -> top-5; khong bo loc category/difficulty. Bootstrap ghep cap theo truy van, 10000 lan, seed 20261126.

Chi phi OpenAI: oa-large embed kho 1584750 token = $0.206; viet lai 61 truy van (gpt-4o-mini, prompt v1) 16119 token, 0 ban viet lai giong truy van goc; embed truy van khong dang ke.

## Model va ban ghim

| id | model / repo | revision HF (hoac API) | dim | trang thai |
|---|---|---|---|---|
| oa-small | text-embedding-3-small | api | 1536 | ok |
| oa-large | text-embedding-3-large | api | 1536 | ok |
| st-minilm | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | e8f8c211226b894fcb81acc59f3b34ba3efd5f42 | 384 | ok |
| st-e5 | intfloat/multilingual-e5-base | d128750597153bb5987e10b1c3493a34e5a4502a | 768 | ok |
| st-bge | BAAI/bge-m3 | 5617a9f61b028005a4858fdac845db406aefb181 | 1024 | ok |

## Golden (SHA-256 file)

| ban | file | sha256 | so voi repo |
|---|---|---|---|
| repo | rag_golden.json | c6fc08022b7964955569bfa6231d76bfee88f41964be78dd845764fd4cd7bdc8 | giong repo |
| repo | rag_golden_holdout.json | 1c75c8d3b39982636eaa6c71305309b3b2c7403f210fda68b9649b235797bb6f | giong repo |
| arp-golden-3c7dae9 | rag_golden.json | 8dd6548cde8d8d52cf8fe58692b6420c68853a95c4078a48f5cc1a2b8ec35eae | KHAC repo |
| arp-golden-3c7dae9 | rag_golden_holdout.json | 674418d84d1725748286962e344616cf58f71da39db89e3bb7961d7de39ec93f | KHAC repo |

## Kiem tra truoc: id relevant khong con trong kho

| golden | tap | truy van | id relevant | id thieu trong kho | id thieu | truy van het dap an | tran recall |
|---|---|---|---|---|---|---|---|
| repo | main | 24 | 37 | 0 | - | 0 | 1.0 |
| repo | holdout | 32 | 43 | 0 | - | 0 | 1.0 |
| arp-golden-3c7dae9 | main | 24 | 38 | 0 | - | 0 | 1.0 |
| arp-golden-3c7dae9 | holdout | 32 | 43 | 0 | - | 0 | 1.0 |

## Cong kiem tra tuong duong

- vector luu vs embed lai 20 chunk bang 3-small: {'n': 20, 'cosine_min': 0.99986, 'cosine_mean': 0.99999}
- trong bo nho vs PgKnowledgeRepository.search (oa-small, raw): {'n_queries': 61, 'identical_top5_order': 61, 'identical_top5_set': 61, 'mean_overlap': 1.0}
- index tren knowledge_chunks: ['knowledge_chunks_content_hash_key', 'knowledge_chunks_filter_idx', 'knowledge_chunks_pkey', 'knowledge_chunks_topic_idx'] -> KHONG co index ANN (hnsw/ivfflat): ai_db tim chinh xac (quet toan bang), nen trung het la dung ky vong

## Ket qua chinh (repo, bo golden trong repo)

### repo / main (n=24 truy van)

**raw, chi vector (CHI SO CHINH)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.833 (20/24) | 0.688 | co so |  |  |  |
| oa-large | 1.000 (24/24) | 0.910 | +0.167 [+0.042, +0.333] | TOT HON (CI > 0) | +0.222 [+0.069, +0.389] | TOT HON (CI > 0) |
| st-minilm | 0.750 (18/24) | 0.626 | -0.083 [-0.292, +0.125] | ngang (CI chua 0) | -0.061 [-0.254, +0.125] | ngang (CI chua 0) |
| st-e5 | 1.000 (24/24) | 0.826 | +0.167 [+0.042, +0.333] | TOT HON (CI > 0) | +0.139 [-0.042, +0.326] | ngang (CI chua 0) |
| st-bge | 1.000 (24/24) | 0.858 | +0.167 [+0.042, +0.333] | TOT HON (CI > 0) | +0.170 [+0.007, +0.347] | TOT HON (CI > 0) |

recall@5 theo nhom:

| Model | vi (n=6) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=24) |
|---|---|---|---|---|---|
| oa-small | 0.333 | 1.000 | 1.000 | 1.000 | 0.833 |
| oa-large | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| st-minilm | 0.500 | 1.000 | 0.833 | 0.600 | 0.750 |
| st-e5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| st-bge | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

**raw+rewrite (LLM viet lai, mot lan, chung cho moi model)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 1.000 (24/24) | 0.847 | co so |  |  |  |
| oa-large | 1.000 (24/24) | 0.910 | +0.000 [+0.000, +0.000] | ngang (CI chua 0) | +0.062 [+0.000, +0.139] | ngang (CI chua 0) |
| st-minilm | 0.917 (22/24) | 0.772 | -0.083 [-0.208, +0.000] | ngang (CI chua 0) | -0.075 [-0.221, +0.062] | ngang (CI chua 0) |
| st-e5 | 1.000 (24/24) | 0.833 | +0.000 [+0.000, +0.000] | ngang (CI chua 0) | -0.014 [-0.097, +0.069] | ngang (CI chua 0) |
| st-bge | 1.000 (24/24) | 0.906 | +0.000 [+0.000, +0.000] | ngang (CI chua 0) | +0.059 [-0.024, +0.146] | ngang (CI chua 0) |

recall@5 theo nhom:

| Model | vi (n=6) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=24) |
|---|---|---|---|---|---|
| oa-small | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| oa-large | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| st-minilm | 0.833 | 1.000 | 0.833 | 1.000 | 0.917 |
| st-e5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| st-bge | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

### repo / holdout (n=32 truy van)

**raw, chi vector (CHI SO CHINH)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.562 (18/32) | 0.372 | co so |  |  |  |
| oa-large | 0.906 (29/32) | 0.772 | +0.344 [+0.156, +0.531] | TOT HON (CI > 0) | +0.400 [+0.269, +0.536] | TOT HON (CI > 0) |
| st-minilm | 0.562 (18/32) | 0.458 | +0.000 [-0.156, +0.156] | ngang (CI chua 0) | +0.086 [-0.042, +0.216] | ngang (CI chua 0) |
| st-e5 | 0.844 (27/32) | 0.672 | +0.281 [+0.094, +0.469] | TOT HON (CI > 0) | +0.299 [+0.146, +0.461] | TOT HON (CI > 0) |
| st-bge | 0.875 (28/32) | 0.755 | +0.312 [+0.156, +0.469] | TOT HON (CI > 0) | +0.382 [+0.240, +0.532] | TOT HON (CI > 0) |

recall@5 theo nhom:

| Model | vi (n=32) | all (n=32) |
|---|---|---|
| oa-small | 0.562 | 0.562 |
| oa-large | 0.906 | 0.906 |
| st-minilm | 0.562 | 0.562 |
| st-e5 | 0.844 | 0.844 |
| st-bge | 0.875 | 0.875 |

**raw+rewrite (LLM viet lai, mot lan, chung cho moi model)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.875 (28/32) | 0.736 | co so |  |  |  |
| oa-large | 0.969 (31/32) | 0.885 | +0.094 [+0.000, +0.188] | ngang (CI chua 0) | +0.149 [+0.020, +0.288] | TOT HON (CI > 0) |
| st-minilm | 0.719 (23/32) | 0.559 | -0.156 [-0.375, +0.062] | ngang (CI chua 0) | -0.177 [-0.377, +0.020] | ngang (CI chua 0) |
| st-e5 | 0.906 (29/32) | 0.716 | +0.031 [-0.062, +0.125] | ngang (CI chua 0) | -0.021 [-0.156, +0.111] | ngang (CI chua 0) |
| st-bge | 0.875 (28/32) | 0.758 | +0.000 [-0.156, +0.156] | ngang (CI chua 0) | +0.021 [-0.131, +0.178] | ngang (CI chua 0) |

recall@5 theo nhom:

| Model | vi (n=32) | all (n=32) |
|---|---|---|
| oa-small | 0.875 | 0.875 |
| oa-large | 0.969 | 0.969 |
| st-minilm | 0.719 | 0.719 |
| st-e5 | 0.906 | 0.906 |
| st-bge | 0.875 | 0.875 |

## Ma tran ket luan (recall@5, hieu so so voi oa-small [95% CI] + ket luan)

| Model | main/raw | holdout/raw | main/raw+rewrite | holdout/raw+rewrite |
|---|---|---|---|---|
| oa-large | +0.167 [+0.042, +0.333] better | +0.344 [+0.156, +0.531] better | +0.000 [+0.000, +0.000] tie (ca hai 100%: tap het kha nang phan biet) | +0.094 [+0.000, +0.188] tie |
| st-minilm | -0.083 [-0.292, +0.125] tie | +0.000 [-0.156, +0.156] tie | -0.083 [-0.208, +0.000] tie | -0.156 [-0.375, +0.062] tie |
| st-e5 | +0.167 [+0.042, +0.333] better | +0.281 [+0.094, +0.469] better | +0.000 [+0.000, +0.000] tie (ca hai 100%: tap het kha nang phan biet) | +0.031 [-0.062, +0.125] tie |
| st-bge | +0.167 [+0.042, +0.333] better | +0.312 [+0.156, +0.469] better | +0.000 [+0.000, +0.000] tie (ca hai 100%: tap het kha nang phan biet) | +0.000 [-0.156, +0.156] tie |

Tom tat theo luat (chi liet ke o nao CI loai 0, khong ngoai suy):

- oa-large: TOT HON (CI > 0): main/raw, holdout/raw; KEM HON (CI < 0): -; ngang (CI chua 0): main/raw+rewrite, holdout/raw+rewrite
- st-minilm: TOT HON (CI > 0): -; KEM HON (CI < 0): -; ngang (CI chua 0): main/raw, main/raw+rewrite, holdout/raw, holdout/raw+rewrite
- st-e5: TOT HON (CI > 0): main/raw, holdout/raw; KEM HON (CI < 0): -; ngang (CI chua 0): main/raw+rewrite, holdout/raw+rewrite
- st-bge: TOT HON (CI > 0): main/raw, holdout/raw; KEM HON (CI < 0): -; ngang (CI chua 0): main/raw+rewrite, holdout/raw+rewrite

## Phu: gop main + holdout (KHONG dung de ket luan thang/thua)

### repo / pooled (n=56 truy van)

**raw, chi vector (CHI SO CHINH)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.679 (38/56) | 0.507 | co so |  |  |  |
| oa-large | 0.946 (53/56) | 0.831 | +0.268 [+0.143, +0.393] | TOT HON (CI > 0) | +0.324 [+0.219, +0.433] | TOT HON (CI > 0) |
| st-minilm | 0.643 (36/56) | 0.530 | -0.036 [-0.161, +0.089] | ngang (CI chua 0) | +0.023 [-0.090, +0.130] | ngang (CI chua 0) |
| st-e5 | 0.911 (51/56) | 0.738 | +0.232 [+0.107, +0.357] | TOT HON (CI > 0) | +0.231 [+0.107, +0.350] | TOT HON (CI > 0) |
| st-bge | 0.929 (52/56) | 0.799 | +0.250 [+0.143, +0.375] | TOT HON (CI > 0) | +0.291 [+0.177, +0.406] | TOT HON (CI > 0) |

recall@5 theo nhom:

| Model | vi (n=38) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=56) |
|---|---|---|---|---|---|
| oa-small | 0.526 | 1.000 | 1.000 | 1.000 | 0.679 |
| oa-large | 0.921 | 1.000 | 1.000 | 1.000 | 0.946 |
| st-minilm | 0.553 | 1.000 | 0.833 | 0.600 | 0.643 |
| st-e5 | 0.868 | 1.000 | 1.000 | 1.000 | 0.911 |
| st-bge | 0.895 | 1.000 | 1.000 | 1.000 | 0.929 |

**raw+rewrite (LLM viet lai, mot lan, chung cho moi model)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.929 (52/56) | 0.784 | co so |  |  |  |
| oa-large | 0.982 (55/56) | 0.896 | +0.054 [+0.000, +0.125] | ngang (CI chua 0) | +0.112 [+0.032, +0.199] | TOT HON (CI > 0) |
| st-minilm | 0.804 (45/56) | 0.651 | -0.125 [-0.250, +0.000] | ngang (CI chua 0) | -0.133 [-0.263, -0.002] | KEM HON (CI < 0) |
| st-e5 | 0.946 (53/56) | 0.766 | +0.018 [-0.036, +0.089] | ngang (CI chua 0) | -0.018 [-0.106, +0.066] | ngang (CI chua 0) |
| st-bge | 0.929 (52/56) | 0.821 | +0.000 [-0.089, +0.089] | ngang (CI chua 0) | +0.037 [-0.059, +0.135] | ngang (CI chua 0) |

recall@5 theo nhom:

| Model | vi (n=38) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=56) |
|---|---|---|---|---|---|
| oa-small | 0.895 | 1.000 | 1.000 | 1.000 | 0.929 |
| oa-large | 0.974 | 1.000 | 1.000 | 1.000 | 0.982 |
| st-minilm | 0.737 | 1.000 | 0.833 | 1.000 | 0.804 |
| st-e5 | 0.921 | 1.000 | 1.000 | 1.000 | 0.946 |
| st-bge | 0.895 | 1.000 | 1.000 | 1.000 | 0.929 |

## Golden arp-golden-3c7dae9 (file KHAC repo)

### arp-golden-3c7dae9 / main (n=24 truy van)

**raw, chi vector (CHI SO CHINH)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.750 (18/24) | 0.592 | co so |  |  |  |
| oa-large | 0.917 (22/24) | 0.814 | +0.167 [+0.042, +0.333] | TOT HON (CI > 0) | +0.222 [+0.069, +0.389] | TOT HON (CI > 0) |
| st-minilm | 0.667 (16/24) | 0.543 | -0.083 [-0.292, +0.125] | ngang (CI chua 0) | -0.049 [-0.236, +0.133] | ngang (CI chua 0) |
| st-e5 | 0.875 (21/24) | 0.722 | +0.125 [-0.042, +0.292] | ngang (CI chua 0) | +0.131 [-0.051, +0.318] | ngang (CI chua 0) |
| st-bge | 0.917 (22/24) | 0.762 | +0.167 [+0.000, +0.375] | ngang (CI chua 0) | +0.170 [+0.004, +0.346] | TOT HON (CI > 0) |

recall@5 theo nhom:

| Model | vi (n=6) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=24) |
|---|---|---|---|---|---|
| oa-small | 0.333 | 1.000 | 1.000 | 0.600 | 0.750 |
| oa-large | 1.000 | 1.000 | 1.000 | 0.600 | 0.917 |
| st-minilm | 0.500 | 1.000 | 0.833 | 0.200 | 0.667 |
| st-e5 | 1.000 | 1.000 | 1.000 | 0.400 | 0.875 |
| st-bge | 1.000 | 1.000 | 1.000 | 0.600 | 0.917 |

**raw+rewrite (LLM viet lai, mot lan, chung cho moi model)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 1.000 (24/24) | 0.868 | co so |  |  |  |
| oa-large | 1.000 (24/24) | 0.910 | +0.000 [+0.000, +0.000] | ngang (CI chua 0) | +0.042 [-0.042, +0.125] | ngang (CI chua 0) |
| st-minilm | 0.833 (20/24) | 0.710 | -0.167 [-0.333, -0.042] | KEM HON (CI < 0) | -0.158 [-0.338, +0.008] | ngang (CI chua 0) |
| st-e5 | 0.917 (22/24) | 0.771 | -0.083 [-0.208, +0.000] | ngang (CI chua 0) | -0.097 [-0.243, +0.035] | ngang (CI chua 0) |
| st-bge | 0.958 (23/24) | 0.858 | -0.042 [-0.125, +0.000] | ngang (CI chua 0) | -0.010 [-0.153, +0.118] | ngang (CI chua 0) |

recall@5 theo nhom:

| Model | vi (n=6) | mixed (n=7) | en (n=6) | no_diacritics (n=5) | all (n=24) |
|---|---|---|---|---|---|
| oa-small | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| oa-large | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| st-minilm | 0.833 | 1.000 | 0.833 | 0.600 | 0.833 |
| st-e5 | 1.000 | 1.000 | 1.000 | 0.600 | 0.917 |
| st-bge | 1.000 | 1.000 | 1.000 | 0.800 | 0.958 |

### arp-golden-3c7dae9 / holdout (n=32 truy van)

**raw, chi vector (CHI SO CHINH)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.500 (16/32) | 0.326 | co so |  |  |  |
| oa-large | 0.906 (29/32) | 0.741 | +0.406 [+0.219, +0.594] | TOT HON (CI > 0) | +0.415 [+0.285, +0.550] | TOT HON (CI > 0) |
| st-minilm | 0.531 (17/32) | 0.448 | +0.031 [-0.094, +0.156] | ngang (CI chua 0) | +0.122 [+0.010, +0.237] | TOT HON (CI > 0) |
| st-e5 | 0.812 (26/32) | 0.616 | +0.312 [+0.125, +0.500] | TOT HON (CI > 0) | +0.290 [+0.137, +0.453] | TOT HON (CI > 0) |
| st-bge | 0.844 (27/32) | 0.723 | +0.344 [+0.188, +0.500] | TOT HON (CI > 0) | +0.398 [+0.249, +0.552] | TOT HON (CI > 0) |

recall@5 theo nhom:

| Model | vi (n=32) | all (n=32) |
|---|---|---|
| oa-small | 0.500 | 0.500 |
| oa-large | 0.906 | 0.906 |
| st-minilm | 0.531 | 0.531 |
| st-e5 | 0.812 | 0.812 |
| st-bge | 0.844 | 0.844 |

**raw+rewrite (LLM viet lai, mot lan, chung cho moi model)**: recall@5 tong + hieu so

| Model | recall@5 | MRR | d recall vs oa-small [95% CI] | ket luan recall | d MRR [95% CI] | ket luan MRR |
|---|---|---|---|---|---|---|
| oa-small | 0.844 (27/32) | 0.700 | co so |  |  |  |
| oa-large | 0.969 (31/32) | 0.860 | +0.125 [+0.031, +0.250] | TOT HON (CI > 0) | +0.160 [+0.030, +0.301] | TOT HON (CI > 0) |
| st-minilm | 0.688 (22/32) | 0.528 | -0.156 [-0.375, +0.062] | ngang (CI chua 0) | -0.172 [-0.374, +0.028] | ngang (CI chua 0) |
| st-e5 | 0.875 (28/32) | 0.669 | +0.031 [-0.062, +0.125] | ngang (CI chua 0) | -0.031 [-0.164, +0.098] | ngang (CI chua 0) |
| st-bge | 0.844 (27/32) | 0.742 | +0.000 [-0.156, +0.156] | ngang (CI chua 0) | +0.042 [-0.108, +0.198] | ngang (CI chua 0) |

recall@5 theo nhom:

| Model | vi (n=32) | all (n=32) |
|---|---|---|
| oa-small | 0.844 | 0.844 |
| oa-large | 0.969 | 0.969 |
| st-minilm | 0.688 | 0.688 |
| st-e5 | 0.875 | 0.875 |
| st-bge | 0.844 | 0.844 |

| Model | main/raw | holdout/raw | main/raw+rewrite | holdout/raw+rewrite |
|---|---|---|---|---|
| oa-large | +0.167 [+0.042, +0.333] better | +0.406 [+0.219, +0.594] better | +0.000 [+0.000, +0.000] tie (ca hai 100%: tap het kha nang phan biet) | +0.125 [+0.031, +0.250] better |
| st-minilm | -0.083 [-0.292, +0.125] tie | +0.031 [-0.094, +0.156] tie | -0.167 [-0.333, -0.042] worse | -0.156 [-0.375, +0.062] tie |
| st-e5 | +0.125 [-0.042, +0.292] tie | +0.312 [+0.125, +0.500] better | -0.083 [-0.208, +0.000] tie | +0.031 [-0.062, +0.125] tie |
| st-bge | +0.167 [+0.000, +0.375] tie | +0.344 [+0.188, +0.500] better | -0.042 [-0.125, +0.000] tie | +0.000 [-0.156, +0.156] tie |

## Van hanh (4 thread CPU, nhu VM e2-standard-4)

LUU Y: do tren may dev 6 nhan / 12 luong, KHONG phai VM e2-standard-4. May co nen ~40% CPU (antivirus, tien trinh khac) va Phase 2 chay song song, nen thoi gian chi mang tinh tham khao (cot cpu he thong tb cho thay muc tai). Truy van do batch 1, bo 3 lan khoi dong; thoi gian OpenAI la vong API (mang), khong so truc tiep voi CPU cuc bo.

| Model | embed kho (s) | nap model (s) | 1 truy van p50 / p95 (ms) | RSS dinh phuc vu / embed kho (MB) | chunk bi cat: tat ca / qa_pair / question | ghi chu |
|---|---|---|---|---|---|---|
| oa-small | n/a (vector luu san) | - | 288.4 / 479.0 | 165 / - | 0 chunk > 8191 token (tiktoken) | vong API (mang) |
| oa-large | 30.9 | - | 280.6 / 572.6 | 166 / - | 0 chunk > 8191 token (tiktoken) | vong API (mang); chi phi embed kho $0.206 |
| st-minilm | 168.4 | 2.01 | 17.3 / 20.2 | 1295 / 1473 | 32.71% / 65.41% / 0.0% @128 | CPU cuc bo; cpu he thong tb 79.6% (embed kho), 47.2% (truy van) |
| st-e5 | 873.1 | 3.87 | 43.4 / 51.5 | 2029 / 2180 | 7.98% / 15.96% / 0.0% @512 | CPU cuc bo; cpu he thong tb 70.2% (embed kho), 44.1% (truy van) |
| st-bge | 3145.1 | 2.55 | 162.5 / 197.4 | 2087 / 2807 | 0.0% / 0.0% / 0.0% @8192 | CPU cuc bo; cpu he thong tb 54.2% (embed kho), 47.4% (truy van) |

## Luat quyet dinh (ghi truoc khi chay)

Mot model chi thang ve chat luong neu khoang tin cay 95% bootstrap cua hieu so (model - oa-small, theo truy van) KHONG chua 0 (ket luan 'TOT HON'/'KEM HON' o tren). Con lai coi la ngang va quyet theo van hanh. Golden chi 24 + 32 truy van nen chi phat hien chenh lech lon; nhieu so sanh (4 model x 2 tap x 2 chien luoc) chua hieu chinh da so sanh. Can duoi CI dung bang 0 tinh la ngang. Chi so chinh theo plan la raw chi vector; duong production la hybrid (BM25 + vector + topic_id, RRF) + viet lai, KHONG do o day nen khong ngoai suy sang production.

## Lenh tai lap

```
cd apps/ai-service
PY=.venv/Scripts/python.exe; M="-m evals.embedding_model_experiment"
$PY -m pip install --use-feature=truststore -r evals/requirements-embedding-experiment.txt
export HF_HUB_DISABLE_XET=1   # may co TLS interception: hf-xet treo khong tai duoc, dung HTTP thuong (truststore inject o entry)
$PY $M load-corpus            # doc ai_db (aie_reader) -> evals/.cache (gitignore)
$PY $M rewrites               # viet lai LLM MOT lan -> .cache/rewrites.json
$PY $M queries --model oa-small
$PY $M embed --model oa-large --max-usd 1 && $PY $M queries --model oa-large
for m in st-minilm st-e5 st-bge; do
  $PY $M embed --model $m                      # lan dau tai model tu HF: thoi gian nap lan nay KHONG dung de bao cao
  HF_HUB_OFFLINE=1 $PY $M queries --model $m  # nap tu cache nong: do nap, p50/p95, RSS
done
$PY $M parity
$PY $M evaluate --out-json <reports>/rag-embedding-results.json --out-md <reports>/rag-embedding-results.md
$PY -m pytest tests/test_embedding_experiment_core.py
```

# RAG 与向量数据库配置说明

本文档说明如何配置 **RAG 接入方案**（知识图谱 vs 纯向量文档）、向量数据库的创建与激活，以及相关环境变量与脚本。

---

## 一、RAG 接入方案（RAG_MODE）

通过环境变量 **`RAG_MODE`** 在两种方案间切换：

| 取值     | 说明 |
|----------|------|
| `graph`  | **知识图谱 + 向量混合检索**：使用 Neo4j 知识图谱 + Neo4j 向量，需启动 Neo4j 并准备 `zhongche_graph_documents.pkl`。 |
| `vector` | **纯向量数据库文档检索**：仅使用 Chroma 向量库，文档来自项目 `doc/` 目录，无需 Neo4j。 |

### 配置方式

- 在**项目根目录**（与 `backend.py` 同级）的 **`.env`** 中设置：
  ```env
  RAG_MODE=vector
  ```
  或
  ```env
  RAG_MODE=graph
  ```
- 未设置时默认为 `graph`。
- 后端会从项目根目录显式加载 `.env`，因此**无论从哪个目录启动服务**，只要 `.env` 在项目根，`RAG_MODE` 都会生效；**vector 模式下不会连接 Neo4j**。

### 后端行为

- **backend 启动时**：
  - 若 `RAG_MODE=vector`：会先检查向量数据库是否存在；若不存在则自动执行 **向量数据库激活脚本**（见下文），再初始化 `fault_analysis_core_vector`。
  - 若 `RAG_MODE=graph`：按原逻辑初始化 `fault_analysis_core`（Neo4j + 图谱数据）。
- **故障分析请求（表单提交）**：
  - **vector 模式**：后端**直接**调用 `fault_analysis_core_vector`（不经过 `inspection_agent`），仅使用向量库与本地嵌入，不连接 Neo4j、不加载图谱相关库。
  - **graph 模式**：经 `inspection_agent.run_fault_analysis`，再调用 `fault_analysis_core`（知识图谱 + 向量）。

---

## 二、向量数据库（Chroma）

### 2.1 路径与集合名

- **持久化目录**：由环境变量 **`VECTOR_DB_DIR`** 指定，默认：
  ```
  <项目根>/data/chroma
  ```
- **集合名称**：由 **`VECTOR_COLLECTION_NAME`** 指定，默认 `patrol_docs`。

在 `.env` 中可覆盖，例如：
```env
VECTOR_DB_DIR=/path/to/my/chroma
VECTOR_COLLECTION_NAME=my_docs
```

- **vector 模式**下后端与巡检智能体**不会连接 Neo4j**，仅使用 Chroma 向量库与本地模型。

### 2.2 向量库是否“存在”的判定

- 若 `VECTOR_DB_DIR` 目录存在，且其中存在 `*.sqlite3` 文件（如 `chroma.sqlite3`），则视为向量库已存在，**不会**在启动时再次执行激活脚本。
- 若不存在，则会在后端启动时自动执行激活脚本（见下一节）。

---

## 三、向量数据库激活脚本

### 3.1 作用

- 当向量库**不存在**时，用于**创建**向量库。
- 将项目 **`doc/`** 目录下的文档按 RAG 推荐配置**分块**并**向量化**后写入 Chroma。
- 过程会向控制台输出**详细日志**（加载文件、分块数量、写入结果等）。

### 3.2 脚本位置与运行方式

- **路径**：`scripts/init_vector_db.py`
- **推荐从项目根目录执行**：
  ```bash
  python scripts/init_vector_db.py
  ```
- 也可由后端在启动时自动调用（当 `RAG_MODE=vector` 且向量库不存在时）。

### 3.3 支持的文档类型

- **.txt**：纯文本，UTF-8。
- **.pdf**：使用 PyPDFLoader。
- **.docx**：使用 Docx2txtLoader。
- 脚本会递归扫描 `doc/` 下所有子目录。

### 3.4 分块配置（适合 RAG 检索）

通过环境变量可调，默认已在 `rag_config.py` 中设置：

| 变量 | 含义 | 默认值 |
|------|------|--------|
| `RAG_CHUNK_SIZE` | 每块字符数 | 800 |
| `RAG_CHUNK_OVERLAP` | 块之间重叠字符数 | 150 |

在 `.env` 中可覆盖，例如：
```env
RAG_CHUNK_SIZE=600
RAG_CHUNK_OVERLAP=100
```

### 3.5 嵌入模型（本地 sentence-transformers，无需代理）

- 向量化使用 **sentence-transformers（HuggingFaceEmbeddings）**，在**本机加载模型并推理**，**不连远端、不需要代理**。
- 通过环境变量 **`EMBEDDING_MODEL_NAME`** 指定模型：
  - 默认：**`BAAI/bge-small-zh-v1.5`**（中文友好，体积较小）。
  - 可改为其它 HuggingFace 模型 id（如 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`）。
  - 也可填**本地目录路径**（如 `./models/bge-small-zh-v1.5`）：模型需已下载到该目录，加载时**完全离线、无需代理**。
- 首次使用某模型 id 时，会从 HuggingFace 下载到本地缓存；之后同一模型**直接读本地缓存，无需网络**。若需完全避免下载时的网络，请先手动下载模型到目录，再将 `EMBEDDING_MODEL_NAME` 设为该目录路径。

---

## 四、文档目录（doc/）

- **路径**：由环境变量 **`DOC_DIR`** 指定，默认为项目根目录下的 **`doc`**。
- 将待参与 RAG 的 **.txt / .pdf / .docx** 放入该目录（可建子目录），然后运行激活脚本或重启后端（在 `RAG_MODE=vector` 且向量库不存在时会自动激活）。
- 若 `doc/` 为空或没有支持格式，脚本会创建“空向量库”（仅结构），并打日志提示。

---

## 五、与 RAG 相关的代码位置标记

- **fault_analysis_core.py**：图谱 + 向量混合 RAG；检索与使用 RAG 的位置已用注释标出（如“这里涉及 RAG”）。
- **fault_analysis_core_vector.py**：纯向量文档 RAG；检索、初始化与使用 RAG 的位置均已标出，且每次 RAG 检索结果会**格式化输出到控制台**。
- **inspection_analysis_demo_vector.py**：基于向量库的 Streamlit Demo，界面中已标明“这里涉及 RAG”。

---

## 六、环境变量汇总

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `RAG_MODE` | RAG 接入方案：`graph` / `vector` | `graph` |
| `VECTOR_DB_DIR` | Chroma 持久化目录 | `<项目根>/data/chroma` |
| `VECTOR_COLLECTION_NAME` | Chroma 集合名 | `patrol_docs` |
| `DOC_DIR` | 待入库文档目录 | `<项目根>/doc` |
| `RAG_CHUNK_SIZE` | 分块大小（字符） | 800 |
| `RAG_CHUNK_OVERLAP` | 分块重叠（字符） | 150 |
| `EMBEDDING_MODEL_NAME` | 本地嵌入模型（HuggingFace id 或本地路径，无需代理） | `BAAI/bge-small-zh-v1.5` |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | 对话 LLM 配置（与现有一致） | - |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j 配置（仅 `RAG_MODE=graph` 时使用） | - |

---

## 七、快速切换为“纯向量 RAG”步骤

1. 在项目根目录创建或编辑 `.env`，设置：
   ```env
   RAG_MODE=vector
   ```
2. 将需要检索的文档放入 **`doc/`**（.txt / .pdf / .docx）。
3. 嵌入使用本地 sentence-transformers，无需额外服务；默认模型首次会下载到本地缓存。
4. （可选）手动执行一次向量库激活：
   ```bash
   python scripts/init_vector_db.py
   ```
5. 启动后端；若向量库不存在，会自动执行激活脚本，再启动服务。
6. 进行故障分析时，将使用 **纯向量文档 RAG**（不连接 Neo4j，向量化使用本机 sentence-transformers，无需代理），且每次 RAG 检索到的文档会在控制台以格式化方式输出。

---

## 八、requirements.txt 与可选依赖

- 向量库方案依赖已写入 **`requirements.txt`**，包括：
  - `chromadb`
  - `langchain-community`、`langchain-text-splitters`
  - `pypdf`、`python-docx`
- 知识图谱方案如需 Neo4j，请按需安装 `langchain-neo4j`、`langchain-ollama` 等（见 requirements 内注释）。

安装全部依赖：
```bash
pip install -r requirements.txt
```

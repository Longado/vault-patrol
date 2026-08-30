# vault-patrol 接力计划(All Things Agentic Hackathon)

- 写于:2026-08-30 晚
- 代码锚点:见 `git log --oneline -1`(R2 后已推进)(接手第一步:`git -C ~/Desktop/Workspace/01_项目/vault-patrol log --oneline -3`,若 HEAD 不是 6d6c2a5 先 `git diff 6d6c2a5..HEAD --stat` 看清差异再动)
- 硬截止:**北京时间 2026-09-01 08:00**(= 8-31 17:00 PDT)。自设提交线 **9-1 02:00**,留 6 小时余量。
- 提交入口:https://allthingsagentichackathon.devpost.com/ (赛道 Taskmaster)

## 0. 一句话

一个事件驱动的 agent:笔记仓一 push,Cloud Run 上的服务克隆仓库 → 代码扫机械腐烂(断链/孤儿/悬空 wikilink)→ Gemini 一次结构化判断五类语义腐烂 → 代码逐条核实证据原文 → 只开一个"减法 PR"。不发明任务,不新建笔记。

## 1. 现状(全部本机实测,未上云)

| 项 | 状态 | 证据命令 | 预期输出 |
|---|---|---|---|
| 单测 | ✅ 8/8 | `cd ~/Desktop/Workspace/01_项目/vault-patrol && .venv/bin/pytest -q` | `8 passed` |
| 机械层 CLI | ✅ | `.venv/bin/python -m patrol run demo-vault --no-model` | 表格 3 行:1 orphan + 2 dangling_wikilink |
| webhook 签名/路由 | ✅ | 见 `app/main.py`;坏签名 401、ping 200、非默认分支 ignored、/run 无 token 401 | — |
| Docker | ✅ | `docker build -q -t vault-patrol:dev . && docker run --rm -e GITHUB_WEBHOOK_SECRET=x -p 18080:8080 -d --name vp vault-patrol:dev && sleep 3 && curl -s localhost:18080/healthz; docker rm -f vp` | `{"ok":true}` |
| Gemini 语义层 | ❌ 未跑过(本机无 key) | — | — |
| GitHub 开 PR 闭环 | ✅ R2 完成(8-30 晚,--no-model) | `GITHUB_TOKEN=$(gh auth token) .venv/bin/python -m patrol repo Longado/vault-patrol-demo --no-model` | `PR: https://github.com/Longado/vault-patrol-demo/pull/1`;重跑只更新同一 PR |
| Cloud Run | ❌ gcloud 已装(`/opt/homebrew/bin/gcloud`),未登录、无项目 | `gcloud auth list` | 当前为空 |
| Firestore | ❌ 代码可选(不设 `FIRESTORE_COLLECTION` 即跳过) | — | — |

已知未验证的假设(接手时优先证伪):
1. 模型 ID `gemini-3.5-flash` 是猜的,R1 第一条命令就是列模型核对。
2. `google-genai` 2.20 的 `response_schema=` 接 pydantic 类 + `resp.parsed` 这个用法按 1.x 文档写的,R1 真跑一次即知。
3. Cloud Run 上 FastAPI `BackgroundTasks` 在响应返回后是否继续拿 CPU:部署必须带 `--no-cpu-throttling`,否则巡查可能被冻结。
4. `patrol/mechanical.py` 的断链检测在 demo-vault 上目前 0 命中(索引里所有链接都真实存在),要演示 delete_line 得在 R2 前往 `MEMORY.md` 加一行指向不存在文件的链接。

## 2. 需要 Eddie 本人做的(代码侧无法代劳)

| # | 事 | 怎么做 | 交付形式 |
|---|---|---|---|
| E1 | Gemini API key | https://aistudio.google.com/apikey 建一个 | 写进仓库根 `.env`(`GEMINI_API_KEY=...`),已 gitignore |
| E2 | GCP 项目 | https://console.cloud.google.com 新建项目(记项目 ID),绑卡开免费试用($300);然后本机 `gcloud auth login && gcloud config set project <ID>` | 项目 ID |
| E3 | GitHub token | 现有 `gh` 登录 token 已有 `repo` scope,MVP 可直接 `GITHUB_TOKEN=$(gh auth token)`;正式提交前换 fine-grained token 只授 demo 仓 | 写进 `.env` |
| E4 | 录视频 + 填 Devpost 表 | R4 备好脚本和素材,你出镜或纯录屏均可 | YouTube 公开链接 |

E1 拿到即可开 R1;E2 拿到即可开 R3;R1/R2/R3 互不阻塞。

## 3. 迭代轮次(每轮:命令 → 预期输出 → 完成判据)

### R1 语义层真跑(约 1 小时,依赖 E1)

```bash
cd ~/Desktop/Workspace/01_项目/vault-patrol && set -a && source .env && set +a
# 1. 核对模型 ID(假设 1)
.venv/bin/python -c "from google import genai; c=genai.Client(); print([m.name for m in c.models.list() if 'gemini' in m.name.lower()][:30])"
#    预期:列表里有 gemini-3.5-* 之类;把真实 ID 写进 .env 的 GEMINI_MODEL
# 2. 真跑 demo-vault
.venv/bin/python -m patrol run demo-vault
```

完成判据:报告里 semantic 命中 **≥4 类**(demo-vault 埋了 5 类,每类对应文件见下表),且 `dropped` 列出的数字 = 模型编造/走样的引用条数(0 也正常)。

| 埋的腐烂 | 文件 | 期望类别 |
|---|---|---|
| stack.md 让人去用 memvid,changelog 说 7-03 已移除 | `tools/stack.md` / `tools/memvid.md` | stale_active_reference |
| starter 钉死 `claude-3-5-sonnet-20240620` | `tools/llm_starter.md` | pinned_old_version |
| commit 格式写了三遍 | `notes/commit_format.md` `git_conventions.md` `commit_howto.md` | overlap_cluster |
| testing "无例外必配测试" vs coding_style "一行改动不配测试" | `notes/testing.md` / `coding_style.md` | hard_conflict |
| recall.md 说 "used daily",recall_log 说 17 天 1 次 | `tools/recall.md` / `notes/recall_log.md` | falsified_claim |

若某类漏检:只改 `prompts/semantic.md`(有 `prompt_version` 头,改完把版本号 +1),不改代码。若 `resp.parsed` 为 None 且 `model_validate_json` 也炸:看 `resp.text` 前 500 字符,多半是 schema 里 Enum 不被支持 → 把 `models.py` 的 Enum 改为 `Literal[...]`。

顺手:`README.md` 还没写,R1 跑通后把真实报告贴进去当示例。

### R2 GitHub 闭环 ✅ 已完成(demo 仓 https://github.com/Longado/vault-patrol-demo,本机副本在 `../vault-patrol-demo/`;主仓 `demo-vault/` 只是文件快照,改示例内容要两边同步)

```bash
# 1. 把 demo-vault 单独建成公开仓(评委可看 PR)
cd ~/Desktop/Workspace/01_项目/vault-patrol/demo-vault
#    先加一条断链好演示 delete_line:
echo '- [Retired planner notes](notes/planner_2025.md)' >> MEMORY.md
git init -q && git add -A && git commit -qm "seed demo vault" && gh repo create Longado/vault-patrol-demo --public --source=. --push
# 2. 本机走完整链路(clone → 判断 → 开 PR)
cd .. && set -a && source .env && set +a
.venv/bin/python -m patrol repo Longado/vault-patrol-demo
```

完成判据:输出最后一行 `PR: https://github.com/Longado/vault-patrol-demo/pull/1`,PR 里 `MEMORY.md` 少了那行断链,`PATROL_REPORT.md` 表格含机械+语义两类。再跑一次同命令 → 因为没设 Firestore,会再次开 PR 但 `open_pr` 走 PATCH 更新同一个 PR(不会开第二个),这是预期。

### R3 Cloud Run 部署(约 1.5 小时,依赖 E2)

```bash
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:$PATH
PROJECT=<E2 的项目 ID>; REGION=us-central1
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com secretmanager.googleapis.com
# Firestore(可选但建议,凑第二个 GCP 服务 + 幂等锚点)
gcloud firestore databases create --location=$REGION --type=firestore-native
# secrets
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "$GITHUB_TOKEN"   | gcloud secrets create github-token --data-file=-
WEBHOOK_SECRET=$(openssl rand -hex 20); printf '%s' "$WEBHOOK_SECRET" | gcloud secrets create webhook-secret --data-file=-
# 部署(源码直推,Cloud Build 打镜像)
cd ~/Desktop/Workspace/01_项目/vault-patrol
gcloud run deploy vault-patrol --source . --region $REGION --allow-unauthenticated \
  --no-cpu-throttling --timeout 600 --memory 1Gi \
  --set-env-vars GEMINI_MODEL=$GEMINI_MODEL,FIRESTORE_COLLECTION=patrol_runs \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,GITHUB_TOKEN=github-token:latest,GITHUB_WEBHOOK_SECRET=webhook-secret:latest
URL=$(gcloud run services describe vault-patrol --region $REGION --format 'value(status.url)'); echo $URL
curl -s $URL/healthz     # 预期 {"ok":true}
# 挂 webhook 到 demo 仓
gh api repos/Longado/vault-patrol-demo/hooks -f name=web -F active=true -f 'events[]=push' \
  -f config[url]=$URL/webhook -f config[content_type]=json -f config[secret]=$WEBHOOK_SECRET
# 触发:往 demo 仓 push 一个改动
cd demo-vault && echo '- [Retired planner notes](notes/planner_2025.md)' >> MEMORY.md && git commit -qam "seed rot" && git push
gcloud run services logs read vault-patrol --region $REGION --limit 30
```

完成判据:日志出现 `patrolled Longado/vault-patrol-demo @ <sha>: N mechanical / M semantic / K dropped → https://github.com/.../pull/N`,PR 页面能打开。Firestore 控制台 `patrol_runs` 集合有一条记录。

坑位:
- Secret Manager 需要给 Cloud Run 的服务账号 `roles/secretmanager.secretAccessor`,报 permission denied 就 `gcloud projects add-iam-policy-binding $PROJECT --member serviceAccount:$(gcloud projects describe $PROJECT --format 'value(projectNumber)')-compute@developer.gserviceaccount.com --role roles/secretmanager.secretAccessor`。
- Firestore 权限同理 `roles/datastore.user`。
- GitHub webhook 10 秒超时,我们返回 202 后台跑,GitHub 那边会显示成功;如果显示失败看 Cloud Run 冷启动时长。
- 如果 `--source` 构建失败,退路:`docker buildx build --platform linux/amd64 -t $REGION-docker.pkg.dev/$PROJECT/vault-patrol/app . --push` 再 `gcloud run deploy --image`。

### R4 提交材料(约 2 小时,可与 R3 并行)

| 材料 | 落点 | 要求 |
|---|---|---|
| README.md | 仓库根 | 问题 → 一句话方案 → 架构图 → 本地 spin-up(`uv venv && uv pip install -e .[dev] && pytest`;`python -m patrol run <vault>`)→ Cloud Run 部署(抄 R3)→ 声明:设计源自作者手写的巡查清单,代码全部提交期内新写 |
| 架构图 | `docs/architecture.md` + 导出 PNG | mermaid:GitHub push → Cloud Run(FastAPI)→ [code] mechanical → [Gemini 3.5, GenAI SDK, 1 call, JSON schema] → [code] verify evidence → GitHub PR;侧边 Firestore anchor |
| Devpost 文案 | `docs/devpost.md` | 字段:项目名 / 一句话 / Inspiration / What it does / How we built it / Challenges / What we learned / 技术栈标签(Gemini, GenAI SDK, Cloud Run, Firestore, FastAPI, Python) |
| 视频脚本 | `docs/video.md` | 4 分钟:0:00-0:40 问题(第二大脑会烂,工具只管加不管删)→ 0:40-1:10 架构图 → 1:10-3:20 实录:push 到 demo 仓 → Cloud Run 日志滚动(露控制台 + .run.app 地址)→ PR 自动出现,点开看报告和 diff → 3:20-4:00 为什么这样设计(判断归模型、循环归代码、证据逐条核实、只做减法) |
| 加分项(可选) | dev.to 一篇 + X/LinkedIn 一条带 #AllThingsAgenticHackathon | 各 +0.2 |

### R5 提交(9-1 02:00 前)

Devpost 表单要填:赛道 Taskmaster;hosted URL 填 Cloud Run 的 `/healthz`;仓库 URL(公开,或私有并共享给 testing@devpost.com 和 cloudhackathons@google.com);视频 YouTube 公开链接;架构图上传。提交后 Cloud Run 可以 `gcloud run services delete` 省钱,FAQ 明说不要求评审期在线。

## 4. 提交后怎么沉淀(比赛跟日常是同一份代码)

- 本机对真 memory 仓跑:`python -m patrol run ~/.claude/projects/-Users-eddie-Desktop-Workspace/memory`,不走 GitHub 不走云。
- 触发仍按巡查协议的三个条件手动跑,**不加 cron**(feedback_memory_patrol 红线)。
- 模型层换回 Claude 只需改 `patrol/semantic.py` 的 `judge()`,契约 `SemanticReport` 不动。
- 真 memory 是中文为主,`prompts/semantic.md` 目前英文;沉淀阶段补一句"findings 的 reasoning 用笔记原语言写"。

## 5. 文件地图

```
patrol/vault.py       读仓 → 不可变快照;NFC 归一化
patrol/mechanical.py  三条确定性检查
patrol/models.py      Finding / SemanticReport / PatrolResult(reasoning 在前;Action 只有减法枚举)
patrol/semantic.py    唯一一次模型调用;prompt 在 prompts/semantic.md 带版本号
patrol/adjudicate.py  代码裁决:verdict=rot + 文件存在 + 引用原文逐字命中 + 去重 + 上限 12
patrol/report.py      渲染 PATROL_REPORT.md;只自动应用"删断链行"这一种编辑
patrol/github_ops.py  clone / push 分支 / 开或更新 PR
patrol/store.py       Firestore 锚点(可选)
patrol/runner.py      控制流:重试 2 次、幂等跳过同 sha、clean 不开 PR
patrol/cli.py         run <path> / repo <owner/name>
app/main.py           /webhook(HMAC 校验)/run(Bearer)/healthz
demo-vault/           埋了全部 8 类腐烂的示例仓
tests/                8 个测试
```

# Alibaba ImageGen Provider 安装使用手册

> 插件名称：alibaba  
> 版本：1.0.0  
> 后端：DashScope 通义万相（Wan2.7 / Wan2.7 Pro）  
> 作者：NousResearch  
> 插件类型：image_gen backend

---

## 1. 实现目标

实现 Hermes `image_gen_provider` 插件接口，解决 hermes 原生 `image_gen_provider` 无法调用阿里云通义万相的问题。该插件接口将通义万相（Wan2.7 / Wan2.7 Pro）注册为 `image_generate` 的后端 provider，使 Hermes 原生生图调用列表包含阿里云通义万相，通过阿里云 DashScope 统一接入层调用通义万相。

- 暴露模型：`wan2.7-image`（标准）、`wan2.7-image-pro`（高级）
- 自动映射 aspect_ratio：`landscape` → `1024*768`，`square` → `1024*1024`，`portrait` → `768*1024`
- 自动把临时 OSS URL 缓存到本地，下游不用处理过期链接
- 失败时返回标准化 error_response，方便上层 fallback 决策

---

## 2. 部署目录位置

```
<HERMES_HOME>/plugins/image_gen/alibaba/
├── __init__.py      # Provider 实现 + register() 入口
├── plugin.yaml      # 插件元数据（name/version/requires_env）
└── __pycache__/     # Python 缓存（自动生成）
```

Hermes 扫描路径：`HERMES_HOME` 指向的 `plugins/image_gen/` 目录。  
单进程单 registry，同路径下只能有一个 `alibaba` provider。

---

## 3. 部署前提

| 前提 | 说明 | 验证方式 |
|------|------|----------|
| Hermes 0.16+ | 支持 plugin.yaml + register_image_gen_provider | `hermes --version` |
| Python 3.11+ | 匹配 runtime 版本 | `python3 --version` |
| `requests` 包 | 运行时动态导入，需可 import | `python3 -c "import requests"` |
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | `echo $DASHSCOPE_API_KEY` |
| EnvironmentFile | Hermes gateway 已挂载 .env | `systemctl show hermes-gateway -p Environment` |
| 插件目录权限 | 文件可读，cache 目录可写 | `ls -l <HERMES_HOME>/plugins/image_gen/alibaba/` |

### 3.1 获取 API Key

1. 打开 https://dashscope.aliyun.com/
2. 登录阿里云账号
3. 控制台 → API Key → 创建 Key

### 3.2 注入环境变量

把 key 写入 Hermes 的 `.env`，不污染全局 env：

```bash
# 追加到 /root/.hermes/.env
echo "DASHSCOPE_API_KEY=<你的完整Key>" >> /root/.hermes/.env
```

如果是 systemd 管理的 gateway，需重载并重启：

```bash
systemctl daemon-reload
systemctl restart hermes-gateway
```

验证：

```bash
systemctl show hermes-gateway -p Environment | grep DASHSCOPE_API_KEY
```

---

## 4. 使用方式

### 4.1 Hermes CLI 验证

```bash
# 在 default profile 下直接调用
hermes -p default -q "请调用 image_generate 工具，prompt 为 '一只猫'"

# 在 social-media profile 下调用
env -u HERMES_DEFAULT_PROFILE hermes -p social-media -q "请调用 image_generate 工具"
```

### 4.2 插件状态查看

```bash
hermes plugins list --plain | grep -i alibaba
# 期望输出：enabled user 1.0.0 alibaba
```

### 4.3 参数说明

| 参数 | 说明 |
|------|------|
| prompt | 中文可，英文优；避免中文标题（模型会乱码） |
| aspect_ratio | `portrait`（3:4 / 768×1024）\| `landscape`（4:3 / 1024×768）\| `square`（1:1 / 1024×1024） |
| model | `wan2.7-image`（默认）\| `wan2.7-image-pro` |

返回示例：

```json
{
  "image": "/root/.hermes/cache/images/alibaba_wan2.7_20260627_205815_ad617709.png",
  "model": "wan2.7-image",
  "provider": "alibaba",
  "aspect_ratio": "portrait",
  "prompt": "...",
  "extra": {"size": "768*1024"}
}
```

### 4.4 通过 Skill 调用（Social-Media 链路）

`xhs-illustrate`、`baoyu-cover-image`、`baoyu-article-illustrator`、`baoyu-xhs-images`、`baoyu-image-gen` 等 skill 在 `image_generate` 可用时会自动路由到此 provider。

---

## 5. 故障排查

| 症状 | 排查 |
|------|------|
| `DASHSCOPE_API_KEY not set` | 确认 `.env` 已写入，`systemctl show hermes-gateway -p Environment` 可见 |
| 401 Unauthorized | key 无效/过期，去 DashScope 控制台刷新 |
| `plugin not found` | 插件目录在 `HERMES_HOME/plugins/image_gen/alibaba/`，且 `plugin.yaml` 存在 |
| 图生成成功但 URL 过期 | 正常现象，插件已做本地缓存；若缓存失败会返回原始 URL |
| `requests` 导入失败 | `pip install requests` 或确保 venv 含 requests |

---

## 6. 限制与成本

- Wan2.7-image 按量付费， prices 以 DashScope 官网为准
- 默认 `n=1`，单次只输出 1 张图
- 单请求 timeout 120s
- 中文 prompt 可，但图片内中文文字渲染不稳定（建议用底层的 image_generate 纯英文 prompt，如需中文标题用 Playwright HTML 渲染兜底）

# Hermes Alibaba ImageGen Provider

实现 Hermes `image_gen_provider` 插件接口，解决 Hermes 原生 `image_gen_provider` 无法调用阿里云通义万相的问题。通过阿里云 DashScope 统一接入层调用通义万相（Wan2.7 / Wan2.7 Pro），使 Hermes `image_generate` 调用列表包含阿里云通义万相。

## 快速开始

```bash
# 部署到 Hermes
cp -r . /root/.hermes/plugins/image_gen/alibaba/
# 确认插件已加载
hermes plugins list --plain | grep -i alibaba
```

## 前提

- Hermes 0.16+
- `DASHSCOPE_API_KEY`（[获取](https://dashscope.aliyun.com/)）

## 完整安装使用手册

见 [INSTALL.md](INSTALL.md)

## 文件

```
plugins/image_gen/alibaba/
├── __init__.py   # Provider 实现 + register()
├── plugin.yaml   # 插件元数据
└── INSTALL.md    # 完整安装使用手册
```

## License

MIT

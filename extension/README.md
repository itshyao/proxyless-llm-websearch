# 🔗 智能 URL 内容解析插件

一个功能强大的浏览器插件，支持对网页 URL 进行智能化解析，支持当前页面、多标签页、自定义 URL 的灵活操作。可配置后端接口，实现多用途内容提取，适用于大语言模型、网页摘要等场景。

**目前插件只支持edge**

## ✨ 插件功能

- 🔍 当前页面解析：一键解析当前访问页面的 URL 内容。
- 🗂 多标签页解析：支持解析浏览器中多个打开的标签页。
- ✏️ 自定义 URL 解析：手动输入任意 URL 进行解析，支持批量输入。
- 💾 结果持久缓存：解析结果将本地缓存，避免重复请求，提升效率。
- ⚙️ 接口地址可配置：可根据需求自定义请求发送的后端 API 地址，灵活接入不同解析服务。

## 🛠 使用须知

要使用此插件，请 先部署后端解析服务，如：

官方推荐后端：[proxyless-llm-websearch](https://github.com/itshyao/proxyless-llm-websearch)

或接入你自己的 API 接口，具体要求查看

```json
{
    "question": str // 输入结构：json
}
```

```json
{
    "data": str // 输出结构：json
}
```

![1](D:/personal/project/proxyless-llm-websearch/extension/img/1.png)

![2](D:/personal/project/proxyless-llm-websearch/extension/img/2.png)

![3](D:/personal/project/proxyless-llm-websearch/extension/img/3.png)

![4](D:/personal/project/proxyless-llm-websearch/extension/img/4.png)

![5](D:/personal/project/proxyless-llm-websearch/extension/img/5.png)
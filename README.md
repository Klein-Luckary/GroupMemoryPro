# GroupMemoryPro

<!--
## 插件开发者详阅

### 开始

此仓库是 LangBot 插件模板，您可以直接在 GitHub 仓库中点击右上角的 "Use this template" 以创建你的插件。  
接下来按照以下步骤修改模板代码：

#### 修改模板代码

- 修改此文档顶部插件名称信息
- 将此文档下方的`<插件发布仓库地址>`改为你的插件在 GitHub· 上的地址
- 补充下方的`使用`章节内容
- 修改`main.py`中的`@register`中的插件 名称、描述、版本、作者 等信息
- 修改`main.py`中的`MyPlugin`类名为你的插件类名
- 将插件所需依赖库写到`requirements.txt`中
- 根据[插件开发教程](https://docs.langbot.app/plugin/dev/tutor.html)编写插件代码
- 删除 README.md 中的注释内容


#### 发布插件

推荐将插件上传到 GitHub 代码仓库，以便用户通过下方方式安装。   
欢迎[提issue](https://github.com/RockChinQ/LangBot/issues/new?assignees=&labels=%E7%8B%AC%E7%AB%8B%E6%8F%92%E4%BB%B6&projects=&template=submit-plugin.yml&title=%5BPlugin%5D%3A+%E8%AF%B7%E6%B1%82%E7%99%BB%E8%AE%B0%E6%96%B0%E6%8F%92%E4%BB%B6)，将您的插件提交到[插件列表](https://github.com/stars/RockChinQ/lists/qchatgpt-%E6%8F%92%E4%BB%B6)

下方是给用户看的内容，按需修改
-->

## 安装

配置完成 [LangBot](https://github.com/RockChinQ/LangBot) 主程序后使用管理员账号向机器人发送命令即可安装：

```
!plugin get https://github.com/Klein-Luckary/GroupMemoryPro.git
```
或查看详细的[插件安装说明](https://docs.langbot.app/plugin/plugin-intro.html#%E6%8F%92%E4%BB%B6%E7%94%A8%E6%B3%95)

## 概述
GroupMemoryPro 是一个基于多维情感模型的伪记忆系统插件，旨在帮助用户管理与其他用户的关系。它能够记录和调整用户之间的关系维度，包括信任度、好感度、互惠性、亲密度和情绪支持。

## 功能
- **关系管理**：自动记录用户之间的互动次数和最后互动时间。
- **评分系统**：根据不同维度计算综合评分。
- **标签管理**：允许管理员为用户添加或删除标签。
- **动态提示**：在用户交互时动态修改提示信息，提供用户关系档案。

## 配置
在代码中，您可以设置管理员用户 ID：
```python
self.admin_users = ["123456790"]  # 替换为实际的管理员用户ID（QQ号）
```
在情景预设中添加自主内容：根据用户多维关系分数调整回复语气和内容；在适当的时候使用(信任度±A、好感度±B、互惠性±C、亲密度±D、情绪支持±E)标记调整分数，可以是小数,可同时调整多维度也可以不调整，调整幅度应不大于1；特别关注用户的特别备注信息等指示。


## 管理员指令
/修改用户 [用户ID] [新评分]：修改指定用户的综合评分。
/增加标签 [用户ID] [标签]：为指定用户添加标签。
/删除标签 [用户ID]：移除指定用户的标签。
/调整维度 [用户ID] [维度] [值]：调整指定用户的某个维度值（信任度、好感度、互惠性、亲密度、情绪支持）。

## 普通用户指令
/查看关系：查看与自己的关系状态，包括综合评分和各个维度的得分。

## 数据存储
所有用户关系数据将保存在 plugins/GroupMemoryPro/data/relation_data.json 文件中。您可以直接查看或编辑该文件以进行数据备份或恢复。

## 日志
插件会记录操作日志，您可以在控制台中查看相关信息，以便于调试和监控。

## 更新画饼
ai自主记忆系统:）

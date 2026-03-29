# 政策金融日报 | Policy & Finance Daily

**日期**: {{date}} | **生成时间**: {{time}} | **覆盖范围**: 近48小时

> **头条摘要**: {{top_story_summary}}

---

## 📊 数据概览

| 地区/机构 | 政策文件 | 项目动态 | 监管通知 | 合计 |
| :--- | :---: | :---: | :---: | :---: |
| 🏙️ 深圳 | {{sz_policy}} | {{sz_project}} | - | {{sz_total}} |
| 🏛️ 北京 | {{bj_policy}} | {{bj_project}} | - | {{bj_total}} |
| 🌏 广东 | {{gd_policy}} | {{gd_project}} | - | {{gd_total}} |
| 🏦 人民银行 | - | - | {{pbc_reg}} | {{pbc_total}} |
| 🛡️ 金融监管总局 | - | - | {{nfra_reg}} | {{nfra_total}} |
| **总计** | **{{total_policy}}** | **{{total_project}}** | **{{total_reg}}** | **{{grand_total}}** |

---

## 🔥 核心焦点 (Top 5)

| 排名 | 标题 | 来源 | 类型 | 核心摘要 | 影响分析 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **{{title_1}}** | {{source_1}} | {{type_1}} | {{summary_1}} | 💡 {{impact_1}} |
| **2** | **{{title_2}}** | {{source_2}} | {{type_2}} | {{summary_2}} | 💡 {{impact_2}} |
| **3** | **{{title_3}}** | {{source_3}} | {{type_3}} | {{summary_3}} | 💡 {{impact_3}} |
| **4** | **{{title_4}}** | {{source_4}} | {{type_4}} | {{summary_4}} | 💡 {{impact_4}} |
| **5** | **{{title_5}}** | {{source_5}} | {{type_5}} | {{summary_5}} | 💡 {{impact_5}} |

---

## 🏙️ 深圳

### 📄 政策文件
{{#if sz_policy_items}}
| 发布日期 | 标题 | 文号 | 摘要 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{sz_policy_table}} |
{{else}}
*暂无新政策文件*
{{/if}}

### 🏗️ 项目动态
{{#if sz_project_items}}
| 发布日期 | 项目名称 | 类型 | 金额/规模 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{sz_project_table}} |
{{else}}
*暂无新项目动态*
{{/if}}

---

## 🏛️ 北京

### 📄 政策文件
{{#if bj_policy_items}}
| 发布日期 | 标题 | 文号 | 摘要 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{bj_policy_table}} |
{{else}}
*暂无新政策文件*
{{/if}}

### 🏗️ 项目动态
{{#if bj_project_items}}
| 发布日期 | 项目名称 | 类型 | 金额/规模 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{bj_project_table}} |
{{else}}
*暂无新项目动态*
{{/if}}

---

## 🌏 广东

### 📄 政策文件
{{#if gd_policy_items}}
| 发布日期 | 标题 | 文号 | 摘要 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{gd_policy_table}} |
{{else}}
*暂无新政策文件*
{{/if}}

### 🏗️ 项目动态
{{#if gd_project_items}}
| 发布日期 | 项目名称 | 类型 | 金额/规模 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{gd_project_table}} |
{{else}}
*暂无新项目动态*
{{/if}}

---

## 🏦 金融监管

### 🏛️ 人民银行
{{#if pbc_items}}
| 发布日期 | 标题 | 类型 | 摘要 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{pbc_table}} |
{{else}}
*暂无新动态*
{{/if}}

### 🛡️ 金融监管总局
{{#if nfra_items}}
| 发布日期 | 标题 | 类型 | 摘要 | 链接 |
| :--- | :--- | :--- | :--- | :--- |
| {{nfra_table}} |
{{else}}
*暂无新动态*
{{/if}}

---

## 📋 政策速览

### 征求意见
{{#if consultation_items}}
{{#each consultation_items}}
- **[{{title}}]({{link}})** ({{source}}) - 截止日期: {{deadline}}
{{/each}}
{{else}}
*暂无征求意见*
{{/if}}

### 即将实施
{{#if upcoming_items}}
{{#each upcoming_items}}
- **[{{title}}]({{link}})** ({{source}}) - 实施日期: {{effective_date}}
{{/each}}
{{else}}
*暂无即将实施政策*
{{/if}}

---

**本报告由 `fin-pol-gov-news` 自动生成**
**数据来源**: 深圳市政府、北京市政府、广东省政府、人民银行、金融监管总局官网

# Lab Sample System

实验室样本管理系统课程设计项目。当前版本已经按数据库脚本重构，Python 客户端以 MySQL 中的表、视图、存储过程和业务约束为中心，不再直接绕过数据库设计写入核心业务数据。

## 技术栈

- MySQL 8.0+
- Python
- Streamlit
- PyMySQL
- Pandas

## 数据库对齐原则

- 样本当前状态以 `samples` 为准。
- 借用单据以 `borrow_records` 为准。
- 历史流水以 `sample_transactions` 为准。
- 样本登记、借用、归还、移位、废弃都通过存储过程执行。
- 样本详情和项目统计等读操作优先复用数据库视图。

## 主要页面与数据库对象映射

- 样本总览：读取 `v_sample_detail`
- 样本登记：调用 `sp_register_sample`
- 样本借用：调用 `sp_borrow_sample`
- 样本归还：调用 `sp_return_sample`
- 样本状态处理：调用 `sp_move_sample` 和 `sp_dispose_sample`
- 记录中心：读取 `v_current_borrowed_samples` 与 `sample_transactions`
- 项目管理：维护 `projects`，查看 `v_project_sample_statistics`

## 项目运行方式

### 本地运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

配置数据库连接（示例）：

```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_USER="user"
$env:DB_PASSWORD="user156"
$env:DB_NAME="lab_db"
```

启动应用：

```bash
streamlit run app_stable.py
```

### Railway 部署方式

1. 在 Railway 创建 MySQL 服务。
2. 在 Railway 创建 Streamlit 服务并连接本仓库。
3. 在 Streamlit 服务中配置 Variables（见下文）。
4. 设置 Custom Start Command（见下文）。
5. 点击 Generate Domain 获取公网访问域名。

## 数据库初始化

在本地或云端 MySQL 中执行以下 SQL 文件：

```sql
SOURCE sql/lab_sample_db.sql;
```

必须使用数据库名：`lab_sample_db`。

重点：应用必须连接 `lab_sample_db`，不要连接默认库 `railway`。

## Railway 配置

### Custom Start Command

```bash
streamlit run app_stable.py --server.port $PORT --server.address 0.0.0.0
```

### Variables

推荐使用独立变量：

```text
DB_HOST=...
DB_PORT=...
DB_USER=...
DB_PASSWORD=...
DB_NAME=lab_sample_db
```

也可使用 URL（2 选 1）：

```text
MYSQL_URL=mysql://<user>:<password>@<host>:<port>/lab_sample_db
```

### Generate Domain

部署成功后，在 Railway 服务页面点击 `Generate Domain`，生成可访问地址。

## 常见报错

报错：

```text
Table 'railway.v_current_borrowed_samples' doesn't exist
```

原因：
应用连接到了错误数据库名 `railway`。

解决：
把 `DB_NAME` 改为 `lab_sample_db`。

如果你使用的是 URL，请把 URL 中数据库名也改成 `lab_sample_db`。

## 最终环境变量说明

在部署环境里明确配置：

```text
DB_HOST=...
DB_PORT=...
DB_USER=...
DB_PASSWORD=...
DB_NAME=lab_sample_db
```

其中 `DB_NAME=lab_sample_db` 是关键项。

## 最终启动命令说明

```bash
streamlit run app_stable.py --server.port $PORT --server.address 0.0.0.0
```

这是本次 Railway 部署成功的必要条件。

## 已实现业务能力

- 样本列表查看、搜索、筛选与状态概览
- 样本登记并自动生成样本编号
- 借用登记与归还闭环处理
- 样本移位和样本废弃
- 当前借用记录与历史流水查询
- 项目列表、统计及增删改查

## 注意事项

- 数据库脚本中的状态值为 `available`、`borrowed`、`disposed`、`returned`、`overdue`，客户端已按此对齐。
- 如果删除项目失败，通常是该项目仍有关联样本，这是受控行为，不建议直接绕过外键约束。
- 如果页面操作成功但列表未刷新，可手动刷新页面再次查看数据库最新状态。

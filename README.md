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

## 初始化数据库
先在 MySQL 中执行以下脚本：

```sql
SOURCE sql/lab_sample_db.sql;
```

该脚本会重建数据库 `lab_sample_db`，并创建基础表、索引、视图、函数、触发器和存储过程。

## 运行方式
安装依赖：

```bash
pip install -r views/requirements.txt
```

配置数据库连接。程序会按以下优先级读取配置：
- Streamlit secrets
- 环境变量
- 默认值

可用配置项：
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

启动应用：

```bash
streamlit run app_stable.py
```

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
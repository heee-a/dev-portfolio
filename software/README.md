# 软件开发：Task API（FastAPI 任务管理服务）

一个教学级但工程完整的 REST 后端：分层架构（路由 / 校验 / 存储）、SQLite 持久化、
Pydantic 参数校验、自动 Swagger 文档、完整的端到端测试。

## 功能

| 端点 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 存活探针 |
| `/tasks` | GET | 列表：`status` 过滤、`q` 标题搜索、`limit/offset` 分页 |
| `/tasks` | POST | 创建（标题 1-100 字符、优先级 1-3、tags ≤5 个，违规返回 422） |
| `/tasks/stats` | GET | 状态统计 + 完成率 |
| `/tasks/{id}` | GET/PATCH/DELETE | 详情 / 部分更新 / 删除（不存在返回 404） |

## 架构与设计决策（面试可展开）

```
main.py（路由：参数绑定 + 状态码，零业务逻辑）
  ├── schemas.py（Pydantic：入参校验集中在这一层）
  └── storage.py（存储层：SQL 语句全在这，换 PostgreSQL 只动这个文件）
```

1. **分层**：路由不写 SQL、存储不解析 HTTP——加一种客户端或换一种数据库
   都只动一层；
2. **配置外置**：数据库路径从环境变量 `TASK_DB_PATH` 读取（12-factor），
   测试因此可以每个用例独立建库，互不污染；
3. **校验前置**：非法优先级/超长标题在 Pydantic 层就返回 422 与字段级错误
   信息，不会打到数据库；
4. **线程安全**：SQLite 写操作用锁串行化；时间戳由服务端生成，客户端不可伪造；
5. **lifespan 管理**：连接随应用生命周期创建销毁，测试通过 lifespan 注入测试库。

## 运行与测试

```bash
pip install fastapi uvicorn
python run.py                    # http://127.0.0.1:8000/docs 看 Swagger

curl -X POST localhost:8000/tasks -H "Content-Type: application/json" \
     -d '{"title": "写周报", "priority": 1, "tags": ["工作"]}'
curl "localhost:8000/tasks?status=todo&limit=10"

pytest tests/test_taskapi.py -q  # 6 项端到端测试（CRUD/校验/分页/404/统计）
```

# 部署状态（DEPLOYMENT STATUS）

> 最后更新：2026-08-19

## 结论：GitHub 是唯一的「非本机」存在

| 位置 | 角色 | 状态 |
|------|------|------|
| 本机 `D:\WORKS\ChairManMao` | 唯一运行/开发环境 | ✅ 在用 |
| GitHub `git@github.com:seconic037/MrMao.git` | 唯一非本机副本（备份/协作） | ✅ 在用 |
| QNAP NAS `192.168.0.11` docker 容器 `chairmanmao` | 旧云端部署 | ❌ **已停止（2026-08-19）** |

## NAS 部署已弃用

- **容器**：`chairmanmao`（原映射 `8341 -> 8000`）已 `docker stop`，状态 `Exited (137)`。
- **重启策略**：`unless-stopped` —— 手动停止后 **NAS 重启不会自动拉起**，无需额外禁用。
- **部署目录**：NAS 上的 `/share/CACHEDEV2_DATA/workspace/chairmanmao`（及大写 `Chairmanmao`）**保留不动**，仅作历史残留，不再更新、不再作为副本。
- **今后**：不再往 NAS 部署本项目。需要离线副本或协作分发，一律走 GitHub。

## 与 `deploy.sh` 的关系

`deploy.sh` 是**部署到独立 EC2（Amazon Linux 2023）** 的脚本，与 NAS docker 部署是两条独立路径，未受本次变更影响。若今后启用 EC2 路径，请先确认其是否仍符合「GitHub 为唯一非本机存在」的约定。

## 端口约定

本机与打包分发的默认端口统一为 **8341**（`.env` 的 `WEB_PORT`，可由用户覆盖）。

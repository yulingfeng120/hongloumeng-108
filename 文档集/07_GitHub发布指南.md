# GitHub 发布指南

### ——三条路径把本书放上GitHub，供后来者取用

## 路径A：GitHub CLI（最接近一键，推荐）

1. 安装命令行工具（Windows）：

   winget install GitHub.cli

2. 登录账号（会打开浏览器授权）：

   gh auth login

3. 在本仓库目录（github仓库/）执行一条命令，即完成"创建远程仓库+推送"两件事：

   gh repo create 仓库名 --public --source . --push

   加 `--private` 则先建私有仓。仓库名建议 `hongloumeng-108` 或 `hongloumeng-guiben-108`。

## 路径B：网页手动（不需要装任何工具）

1. 登录 github.com，右上角 + → New repository；填仓库名，**不要**勾选自动生成README/license（本地已有）。
2. 回到本地仓库目录执行：

   git remote add origin https://github.com/你的用户名/仓库名.git
   git push -u origin main

   推送时弹出的浏览器授权（或要求Personal Access Token）按提示完成即可。

## 路径C：GitHub Desktop（图形界面）

安装 GitHub Desktop → File → Add local repository（选本目录）→ Publish repository 按钮，即发布。适合不想碰命令行的情况。

## 发布压缩包（Release）

仓库页右侧 Releases → Draft a new release → 新建标签（如 v1.0）→ 拖入《红楼梦一百零八回（开源共享版）.zip》→ Publish。Release 是分发压缩包的标准位置，访问者无需懂git也能下载。

## 仓库维护建议

- 描述与标签：简介可写"以癸酉本为骨架、脂批为法度、程高本为文貌的一百零八回整理本"；标签（Topics）建议：hongloumeng、chinese-literature、digital-humanities、ai-collaboration。
- README 自动渲染：仓库首页自动显示 README.md，即项目门面。
- 提交身份：本地提交署名为"西域吃沙的峰兄"+ noreply 邮箱；如需改为真实GitHub账号，推送前执行：

  git config user.email 你的GitHub邮箱
  git commit --amend --reset-author --no-edit

- 体积：仓库约35MB，最大单文件（对照本PDF）约11MB，均低于GitHub 100MB限制，无需LFS。
- 版权：仓库已含 LICENSE（CC BY-NC-SA 4.0）；鬼本底本的权利状况声明见 README，公开后如有权利人异议请依法处理。

## 更新流程（日后修订）

改任何文件后：

git add -A
git commit -m "修订说明"
git push

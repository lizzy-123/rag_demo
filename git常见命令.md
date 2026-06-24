# git --version //版本号
# git config --global user.name "你的GitHub用户名"
# git config --global user.email "你注册GitHub的邮箱"
    - 配置你的 GitHub 账号用户名 & 邮箱（和 GitHub 注册信息一致）

# 1. 初始化本地Git仓库（仅第一次运行）
git init

# 2. 将所有代码加入待提交清单
git add .

# 3. 提交代码，引号内是本次更新说明，可自定义
git commit -m "第一次上传完整代码"

# 4. 关联远程GitHub仓库（粘贴刚才复制的HTTPS仓库地址）
git remote add origin https://github.com/你的用户名/仓库名.git

# 5. 推送代码到GitHub主分支main
git push -u origin main

如果提示 remote origin already exists，执行这条覆盖：
git remote set-url origin https://github.com/你的用户名/你的仓库名.git

1. 创建开发分支（示例分支名 dev，可自定义）
bash
运行
git checkout -b dev
这条命令 = 创建分支 + 自动切换到 dev 分支
2. 在 dev 分支修改代码后提交推送
bash
运行
# 修改完代码后执行
git add .
git commit -m "开发分支：新增XX功能"
git push origin dev
3. 以后切换分支命令
切回主分支查看稳定版本
bash
运行
git checkout main
切回开发分支继续开发
bash
运行
git checkout dev
4. 开发完成后把 dev 分支代码合并到 main（上线主版本）
bash
运行
# 先切回main
git checkout main
# 把dev分支的改动合并到main
git merge dev
# 推送合并后的主版本到GitHub
git push origin main



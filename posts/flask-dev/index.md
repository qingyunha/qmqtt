+++
date = "2016-05-21T21:48:31+08:00"
title = "成为Flask贡献者"
categories = ["wiki"]

+++

当你clone下Flask项目之后：

1. 使用virtualenv或者venv创建虚拟环境

2. `pip install -e .`用开发者模式安装本地Flask

3. `py.test tests`运行测试代码 (如果不用上面的方法，py.test很难用起来)

4. 在github fork后`git add remote fork https://github.com/<username>/flask.git`

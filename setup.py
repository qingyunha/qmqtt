from setuptools import  setup

setup(
    name="qmqtt",       
    description="A simple and complete implementation of MQTT protocol",
    version="0.1.0",
    author="Tao Qingyun",
    author_email="84576765@qq.com",
    url="https://github.com/qingyunha/qmqtt",
    packages=["qmqtt"],
    keywords="MQTT asyncio",
    entry_points={"console_scripts": ["qmqtt = qmqtt.__main__:main"]},
)

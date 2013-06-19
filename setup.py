from setuptools import setup

setup(name='prices',
      version='1.0',
      description='prices app',
      author='wurdum',
      author_email='wurdum.my@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',
      install_requires=['Flask>=0.7.2', 'beautifulsoup4>=4.2.0', 'pymongo>=2.5.1', 'eventlet'],
)

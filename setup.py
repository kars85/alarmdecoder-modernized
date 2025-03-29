from setuptools import setup, find_packages

setup(
    name='alarmdecoder',
    version='1.0.0',
    description='Modernized Python interface for the AlarmDecoder (AD2) family of alarm devices',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Nu Tech Software Solutions, Inc.',
    author_email='general@support.nutech.com',
    url='https://github.com/nutechsoftware/alarmdecoder',
    license='MIT',
    packages=find_packages(exclude=['test', 'tests']),
    python_requires='>=3.11',
    install_requires=[
        'pyserial>=3.5',
    ],
    extras_require={
        'dev': ['pytest', 'mypy', 'flake8'],
    },
    entry_points={
        'console_scripts': [
            'ad2-firmwareupload = alarmdecoder.util.ad2_firmwareupload:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Home Automation',
        'Topic :: Security',
    ],
    include_package_data=True,
    zip_safe=False,
)

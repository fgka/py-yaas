# Development 

Below how to bootstrap your python environment, so it is sandboxed.

## Development Environment Using Pyenv and Virtualenv

Install:

* (optional) [pyenv](https://github.com/pyenv/pyenv);
* [virtualenv](https://virtualenv.pypa.io/en/latest/).

### macOS

You need `Xcode`:

```bash
xcode-select --install
```

### (Optional) Pyenv

For macOS follow [https://gist.github.com/eliangcs/43a51f5c95dd9b848ddc](https://gist.github.com/eliangcs/43a51f5c95dd9b848ddc).
You might also need [https://github.com/jiansoung/issues-list/issues/13#issuecomment-478575934](https://github.com/jiansoung/issues-list/issues/13#issuecomment-478575934).

Set python 3.10 as default:

```basn
pyenv install 3.10.6
```

Set pyenv defaults:
```bash
pyenv global 3.10.6
pyenv local 3.10.6
```

### Virtualenv

Install Virtualenv and update `pip`:

```bash
pip3 install -U pip virtualenv
```

Create virtualenv:

```bash
virtualenv -p python3 -q .venv
```

To activate your python virtualenv:

```bash
. .venv/bin/activate
```

Validate with:

```bash
python --version
python3 --version
```

Expected:

```text
Python 3.10.6
Python 3.10.6
```

Install packages:

```bash
pip3 install -U pip wheel setuptools
```

## Install all dependencies

Install packages:

```bash
pip3 install ".[all]" \
  &&  pip3 uninstall --yes $(python3 ./setup.py --name)
```

## Auto-formatting with black

In this project black was chosen for the auto-formatter.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

### Install black with vim

After following the instructions I have in my ``~/.vimrc`` the following:

```vimrc
" black formatter
let g:black_linelength=100
let g:black_skip_string_normalization=1
autocmd BufWritePre *.py execute ':Black'
```

# Deployment

## Install

Will add the library to your local python environment (if you are using virtualenv, it will be added to it only).

```bash
python3 ./setup.py install
```

## Generate Wheel file

For advanced usage of Wheel files see, for instance, [Python on Wheels](https://lucumr.pocoo.org/2014/1/27/python-on-wheels/).

```bash
python3 ./setup.py bdist_wheel --universal
```

Check the files:

```bash
ls dist
```

Expected:

```text
py_yaas_playground-1.0-py2.py3-none-any.whl
```

## Build Docker Image

```bash
docker build -t yaas-playground .
```

### Test Docker Image Locally

Start image:

```bash
PORT=8080
CONFIG_BUCKET_NAME="yaas_cache"
CONFIG_OBJECT_PATH="yaas.cfg"
docker run \
  --publish 127.0.0.1:${PORT}:${PORT} \
  --volume "${HOME}/.config/gcloud/application_default_credentials.json":/gcp/creds.json:ro \
  --env GOOGLE_APPLICATION_CREDENTIALS=/gcp/creds.json \
  --env PORT=${PORT} \
  --env CONFIG_BUCKET_NAME=${CONFIG_BUCKET_NAME} \
  --env CONFIG_OBJECT_PATH=${CONFIG_OBJECT_PATH} \
  -it yaas-playground   
```

Test the image:

```bash
curl http://localhost:8080/config
```

## PyCharm Users

You need to add ``--no-cov`` to your `Run/Debug` settings.
Below are the instructions on how to do it.
Tested with `PyCharm 2022.2.1 (Professional Edition)` for macOS.

### Menu `Run` click on `Edit Configurations...`:

![menu](./doc/0_pycharm_run_menu.png)

### Click `Edit configuration templates...`

![template](./doc/1_pycharm_edit_template.png)

### Select `Python tests/Autodetect`

Add `--no-cov` to `Additional Arguments` field:

![autodetect](./doc/2_pycharm_autodetect_template.png)

### Select `Python tests/pytest`

Add `--no-cov` to `Additional Arguments` field:

![pytest](./doc/3_pycharm_pytest_template.png)
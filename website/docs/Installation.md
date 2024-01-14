# AutoGen Installation Guide

AutoGen is a versatile tool that can be installed and run in Docker or locally using a virtual environment. Below are detailed instructions for both methods.

## Option 1: Install and Run AutoGen in Docker

### Step 1: Install Docker

- Follow the [official Docker installation instructions](https://docs.docker.com/get-docker/).
- For Mac users: Consider using [colima](https://smallsharpsoftwaretools.com/tutorials/use-colima-to-run-docker-containers-on-macos/) as an alternative if you encounter issues with the Docker daemon.

### Step 2: Build a Docker Image

AutoGen provides Dockerfiles for building docker images. Choose one based on your needs:

- For a basic setup (includes common Python libraries and essential dependencies):

  ```bash
  docker build -f samples/dockers/Dockerfile.base -t autogen_img https://github.com/microsoft/autogen.git#main
  ```
  
- For advanced features (includes additional dependencies):

  ```bash
  docker build -f samples/dockers/Dockerfile.full -t autogen_full_img https://github.com/microsoft/autogen.git
  ```

  To check if the image is created successfully, use `docker images`.

### Step 3: Run AutoGen Applications from Docker Image

To run an application built with AutoGen (e.g., a script named `twoagent.py`), mount your code and execute it in Docker:

```bash
docker run -it -v `pwd`/myapp:/myapp autogen_img:latest python /myapp/main_twoagent.py
```

## Option 2: Install AutoGen Locally Using Virtual Environment

### Option a: venv

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv pyautogen
   source pyautogen/bin/activate
   ```

2. To exit the virtual environment:

   ```bash
   deactivate
   ```

### Option b: conda

1. Create and activate a Conda environment:

   ```bash
   conda create -n pyautogen python=3.10
   conda activate pyautogen
   ```

2. To exit Conda environment:

   ```bash
   conda deactivate
   ```

### Option c: poetry

1. Initialize and activate a Poetry environment:

   ```bash
   poetry init
   poetry shell
   poetry add pyautogen
   ```

2. To exit the Poetry environment:

   ```bash
   exit
   ```

## Python Version Compatibility

AutoGen requires **Python version >= 3.8, < 3.12**. Install it using pip:

```bash
pip install pyautogen
```

Refer to the [Migration guide to v0.2](/autogen/docs/Installation#migration-guide-to-v0.2) for updates and changes.

### Optional Dependencies

- **Docker**: Highly recommended for code execution. Install with `pip install docker`.
- **Blendsearch**: For hyperparameter optimization. Install with `pip install "pyautogen[blendsearch]<0.2"`.
- **Retrievechat**: For retrieval-augmented tasks. Install with `pip install "pyautogen[retrievechat]"`.
- **Teachability**: For teachable agents. Install with `pip install "pyautogen[teachable]"`.
- **LMM Agents**: For multimodal conversable agents. Install with `pip install "pyautogen[lmm]"`.
- **Mathchat**: For math problem-solving agents. Install with `pip install "pyautogen[mathchat]<0.2"`.



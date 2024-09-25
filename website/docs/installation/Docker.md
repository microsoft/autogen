# Docker

Docker, an indispensable tool in modern software development, offers a compelling solution for AutoGen's setup. Docker allows you to create consistent environments that are portable and isolated from the host OS. With Docker, everything AutoGen needs to run, from the operating system to specific libraries, is encapsulated in a container, ensuring uniform functionality across different systems. The Dockerfiles necessary for AutoGen are conveniently located in the project's GitHub repository at [https://github.com/microsoft/autogen/tree/main/.devcontainer](https://github.com/microsoft/autogen/tree/main/.devcontainer).

**Pre-configured DockerFiles**: The AutoGen Project offers pre-configured Dockerfiles for your use. These Dockerfiles will run as is, however they can be modified to suit your development needs. Please see the README.md file in autogen/.devcontainer

- **autogen_base_img**: For a basic setup, you can use the `autogen_base_img` to run simple scripts or applications. This is ideal for general users or those new to AutoGen.
- **autogen_full_img**: Advanced users or those requiring more features can use `autogen_full_img`. Be aware that this version loads ALL THE THINGS and thus is very large. Take this into consideration if you build your application off of it.

## Step 1: Install Docker

- **General Installation**: Follow the [official Docker installation instructions](https://docs.docker.com/get-docker/). This is your first step towards a containerized environment, ensuring a consistent and isolated workspace for AutoGen.

- **For Mac Users**: If you encounter issues with the Docker daemon, consider using [colima](https://smallsharpsoftwaretools.com/tutorials/use-colima-to-run-docker-containers-on-macos/). Colima offers a lightweight alternative to manage Docker containers efficiently on macOS.

## Step 2: Build a Docker Image

AutoGen now provides updated Dockerfiles tailored for different needs. Building a Docker image is akin to setting the foundation for your project's environment:

- **Autogen Basic**: Ideal for general use, this setup includes common Python libraries and essential dependencies. Perfect for those just starting with AutoGen.

  ```bash
  docker build -f .devcontainer/Dockerfile -t autogen_base_img https://github.com/microsoft/autogen.git#main
  ```

- **Autogen Advanced**: Advanced users or those requiring all the things that AutoGen has to offer `autogen_full_img`

  ```bash
  docker build -f .devcontainer/full/Dockerfile -t autogen_full_img https://github.com/microsoft/autogen.git#main
  ```

## Step 3: Run AutoGen Applications from Docker Image

Here's how you can run an application built with AutoGen, using the Docker image:

1. **Mount Your Directory**: Use the Docker `-v` flag to mount your local application directory to the Docker container. This allows you to develop on your local machine while running the code in a consistent Docker environment. For example:

   ```bash
   docker run -it -v $(pwd)/myapp:/home/autogen/autogen/myapp autogen_base_img:latest python /home/autogen/autogen/myapp/main.py
   ```

   Here, `$(pwd)/myapp` is your local directory, and `/home/autogen/autogen/myapp` is the path in the Docker container where your code will be located.

2. **Mount your code:** Now suppose you have your application built with AutoGen in a main script named `twoagent.py` ([example](https://github.com/microsoft/autogen/blob/main/test/twoagent.py)) in a folder named `myapp`. With the command line below, you can mount your folder and run the application in Docker.

   ```python
   # Mount the local folder `myapp` into docker image and run the script named "twoagent.py" in the docker.
   docker run -it -v `pwd`/myapp:/myapp autogen_img:latest python /myapp/main_twoagent.py
   ```

3. **Port Mapping**: If your application requires a specific port, use the `-p` flag to map the container's port to your host. For instance, if your app runs on port 3000 inside Docker and you want it accessible on port 8080 on your host machine:

   ```bash
   docker run -it -p 8080:3000 -v $(pwd)/myapp:/myapp autogen_base_img:latest python /myapp
   ```

   In this command, `-p 8080:3000` maps port 3000 from the container to port 8080 on your local machine.

4. **Examples of Running Different Applications**: Here is the basic format of the docker run command.

```bash
docker run -it -p {WorkstationPortNum}:{DockerPortNum} -v {WorkStation_Dir}:{Docker_DIR} {name_of_the_image} {bash/python} {Docker_path_to_script_to_execute}
```

- _Simple Script_: Run a Python script located in your local `myapp` directory.

  ```bash
  docker run -it -v `pwd`/myapp:/myapp autogen_base_img:latest python /myapp/my_script.py
  ```

- _Web Application_: If your application includes a web server running on port 5000.

  ```bash
  docker run -it -p 8080:5000 -v $(pwd)/myapp:/myapp autogen_base_img:latest
  ```

- _Data Processing_: For tasks that involve processing data stored in a local directory.

  ```bash
  docker run -it -v $(pwd)/data:/data autogen_base_img:latest python /myapp/process_data.py
  ```

## Additional Resources

- Details on all the Dockerfile options can be found in the [Dockerfile](https://github.com/microsoft/autogen/blob/main/.devcontainer/README.md) README.
- For more information on Docker usage and best practices, refer to the [official Docker documentation](https://docs.docker.com).
- Details on how to use the Dockerfile dev version can be found on the [Contributor Guide](/docs/contributor-guide/docker).

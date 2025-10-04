# Embedchain Chat with PDF App

You can easily create and deploy your own `Chat-with-PDF` App using Embedchain.

Checkout the live demo we created for [chat with PDF](https://embedchain.ai/demo/chat-pdf).

Here are few simple steps for you to create and deploy your app:

1. Fork the embedchain repo from [Github](https://github.com/embedchain/embedchain).

If you run into problems with forking, please refer to [github docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) for forking a repo.

2. Navigate to `chat-pdf` example app from your forked repo:

```bash
cd <your_fork_repo>/examples/chat-pdf
```

3. Run your app in development environment with simple commands

```bash
pip install -r requirements.txt
ec dev
```

Feel free to improve our simple `chat-pdf` streamlit app and create pull request to showcase your app [here](https://docs.embedchain.ai/examples/showcase)

4. You can easily deploy your app using Streamlit interface

Connect your Github account with Streamlit and refer this [guide](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app) to deploy your app.

You can also use the deploy button from your streamlit website you see when running `ec dev` command.

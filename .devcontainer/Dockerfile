# Note: You can use any Debian/Ubuntu based image you want.
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# [Optional] Uncomment this section to install additional OS packages.

# Adding all potentially useful dev tools I can think of... 
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends curl wget ssh git unzip jq net-tools nmap telnet traceroute iputils-ping dnsutils socat openssh-client rsync expect whois

# Adding kubectl and Helm for agents to communicate with K8s clusters
#https://stackoverflow.com/questions/63994247/how-to-install-kubectl-and-helm-using-dockerfile
RUN curl -LO https://dl.k8s.io/release/v1.24.0/bin/linux/amd64/kubectl && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
RUN wget https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 && \
    chmod 700 get-helm-3 &&\
    ./get-helm-3

#ENV KUBECONFIG=/workspaces/autogen/kubeconfig

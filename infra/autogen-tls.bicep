// Bicep template for deploying AutoGen with TLS
param location string = resourceGroup().location
param containerAppName string = 'autogen-host'
param keyVaultName string
param serverCertSecretName string = 'autogen-server-cert'
param serverKeySecretName string = 'autogen-server-key'

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource environment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${containerAppName}-env'
  location: location
  properties: {
    zoneRedundant: false
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      secrets: [
        {
          name: 'server-cert'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/${serverCertSecretName}'
          identity: 'system'
        }
        {
          name: 'server-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/${serverKeySecretName}'
          identity: 'system'
        }
      ]
      ingress: {
        external: true
        targetPort: 50051
        transport: 'grpc'
      }
    }
    template: {
      containers: [
        {
          name: 'autogen-host'
          image: 'mcr.microsoft.com/autogen/host:latest' // Replace with your image
          env: [
            {
              name: 'AUTOGEN_TLS_CERT'
              secretRef: 'server-cert'
            }
            {
              name: 'AUTOGEN_TLS_KEY'
              secretRef: 'server-key'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn

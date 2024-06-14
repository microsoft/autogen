param name string
param location string = resourceGroup().location
param tags object = {}

param applicationInsightsName string
param identityName string
param serviceName string = 'gh-flow'
param sandboxImage string = 'mcr.microsoft.com/dotnet/sdk:7.0'


param containerAppsEnvironmentName string
param containerRegistryName string
param storageAccountName string
param cosmosAccountName string

@secure()
param githubAppKey string
param githubAppId string
param githubAppInstallationId string
param rgName string
param aciShare string
param openAIServiceType string
param openAIServiceId string
param openAIDeploymentId string
param openAIEmbeddingId string
param openAIEndpoint string
@secure()
param openAIKey string
param qdrantEndpoint string

resource ghFlowIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

resource storage 'Microsoft.Storage/storageAccounts@2021-09-01' existing = {
  name: storageAccountName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2022-08-15' existing = {
  name: cosmosAccountName
}

var contributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
var wehbookSecret = uniqueString(resourceGroup().id)

resource rgContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, resourceGroup().id, contributorRole)
  properties: {
    roleDefinitionId: contributorRole
    principalType: 'ServicePrincipal'
    principalId: app.outputs.identityPrincipalId
  }
}

module app '../core/host/container-app.bicep' = {
  name: '${serviceName}-ghflow'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityType: 'UserAssigned'
    identityName: ghFlowIdentity.name
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    containerCpuCoreCount: '2.0'
    containerMemory: '4.0Gi'
    env: [
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: applicationInsights.properties.ConnectionString
      }
      {
        name: 'SANDBOX_IMAGE'
        value: sandboxImage
      }
      {
        name: 'GithubOptions__AppKey'
        value: githubAppKey
      }
      {
        name: 'GithubOptions__AppId'
        value: githubAppId
      }
      {
        name: 'GithubOptions__InstallationId'
        value: githubAppInstallationId
      }
      {
        name: 'GithubOptions__WebhookSecret'
        value: wehbookSecret
      }
      {
        name: 'AzureOptions__SubscriptionId'
        value: subscription().subscriptionId
      }
      {
        name: 'AzureOptions__Location'
        value: location
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: ghFlowIdentity.properties.clientId
      }
      {
        name: 'AzureOptions__ContainerInstancesResourceGroup'
        value: rgName
      }
      {
        name: 'AzureOptions__FilesAccountKey'
        value: storage.listKeys().keys[0].value
      }
      {
        name: 'AzureOptions__FilesShareName'
        value: aciShare
      }
      {
        name: 'AzureOptions__FilesAccountName'
        value: storageAccountName
      }
      {
        name: 'AzureOptions__CosmosConnectionString'
        value: cosmos.listConnectionStrings().connectionStrings[0].connectionString
      }
      {
        name: 'OpenAIOptions__ServiceType'
        value: openAIServiceType
      }
      {
        name: 'OpenAIOptions__ServiceId'
        value: openAIServiceId
      }
      {
        name: 'OpenAIOptions__DeploymentOrModelId'
        value: openAIDeploymentId
      }
      {
        name: 'OpenAIOptions__EmbeddingDeploymentOrModelId'
        value: openAIEmbeddingId
      }
      {
        name: 'OpenAIOptions__Endpoint'
        value: openAIEndpoint
      }
      {
        name: 'OpenAIOptions__ApiKey'
        value: openAIKey
      }
      {
        name: 'QdrantOptions__Endpoint'
        value: qdrantEndpoint
      }
      {
        name: 'QdrantOptions__VectorSize'
        value: '1536'
      }
    ]
    targetPort: 5274
  }
}


output SERVICE_TRANSLATE_API_IDENTITY_PRINCIPAL_ID string = app.outputs.identityPrincipalId
output SERVICE_TRANSLATE_API_NAME string = app.outputs.name
output SERVICE_TRANSLATE_API_URI string = app.outputs.uri
output WEBHOOK_SECRET string = wehbookSecret

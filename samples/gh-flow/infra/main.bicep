targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@secure()
param githubAppKey string
param githubAppId string
param githubAppInstallationId string
param openAIServiceType string
param openAIServiceId string
param openAIDeploymentId string
param openAIEmbeddingId string
param openAIEndpoint string
@secure()
param openAIKey string

param applicationInsightsDashboardName string = ''
param applicationInsightsName string = ''
param logAnalyticsName string = ''
param resourceGroupName string = ''
param storageAccountName string = ''
param containerAppsEnvironmentName string = ''
param containerRegistryName string = ''
param ghFlowServiceName string = ''
param cosmosAccountName string = ''


var aciShare = 'acishare'
var qdrantShare = 'qdrantshare'

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module storage './core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
    fileShares: [ 
      aciShare
      qdrantShare
   ]
  }
}

// Monitor application with Azure Monitor
module monitoring './core/monitor/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: !empty(applicationInsightsDashboardName) ? applicationInsightsDashboardName : '${abbrs.portalDashboards}${resourceToken}'
  }
}

// Container apps host (including container registry)
module containerApps './core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: !empty(containerAppsEnvironmentName) ? containerAppsEnvironmentName : '${abbrs.appManagedEnvironments}${resourceToken}'
    containerRegistryName: !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
    applicationInsightsName: monitoring.outputs.applicationInsightsName
  }
}

module qdrant './core/database/qdrant/qdrant-aca.bicep' = {
  name: 'qdrant-deploy'
  scope: rg
  params: {
    location: location
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    shareName: qdrantShare
    storageName: storage.outputs.name
  }
}

// The application database
module cosmos './app/db.bicep' = {
  name: 'cosmos'
  scope: rg
  params: {
    accountName: !empty(cosmosAccountName) ? cosmosAccountName : '${abbrs.documentDBDatabaseAccounts}${resourceToken}'
    databaseName: 'devteam'
    location: location
    tags: tags
  }
}

module ghFlow './app/gh-flow.bicep' = {
  name: 'gh-flow'
  scope: rg
  params: {
    name: !empty(ghFlowServiceName) ? ghFlowServiceName : '${abbrs.appContainerApps}ghflow-${resourceToken}'
    location: location
    tags: tags
    identityName: '${abbrs.managedIdentityUserAssignedIdentities}ghflow-${resourceToken}'
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName:containerApps.outputs.registryName
    storageAccountName: storage.outputs.name
    aciShare: aciShare
    githubAppId: githubAppId
    githubAppInstallationId: githubAppInstallationId
    githubAppKey: githubAppKey
    openAIDeploymentId: openAIDeploymentId
    openAIEmbeddingId: openAIEmbeddingId
    openAIEndpoint: openAIEndpoint
    openAIKey: openAIKey
    openAIServiceId: openAIServiceId
    openAIServiceType: openAIServiceType
    qdrantEndpoint: 'https://${qdrant.outputs.fqdn}'
    rgName: rg.name
    cosmosAccountName: cosmos.outputs.accountName
  }
}


// App outputs
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = subscription().tenantId
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_RESOURCE_GROUP_NAME string = rg.name
output AZURE_FILESHARE_NAME string = aciShare
output AZURE_FILESHARE_ACCOUNT_NAME string = storage.outputs.name
output QDRANT_ENDPOINT string = 'https://${qdrant.outputs.fqdn}'
output WEBHOOK_SECRET string = ghFlow.outputs.WEBHOOK_SECRET

// Data outputs
output AZURE_COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_COSMOS_CONNECTION_STRING_KEY string = cosmos.outputs.connectionStringKey
output AZURE_COSMOS_DATABASE_NAME string = cosmos.outputs.databaseName

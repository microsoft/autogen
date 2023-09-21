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

param apiServiceName string = ''
param applicationInsightsDashboardName string = ''
param applicationInsightsName string = ''
param appServicePlanName string = ''
param logAnalyticsName string = ''
param resourceGroupName string = ''
param storageAccountName string = ''
param containerAppsEnvironmentName string = ''
param containerRegistryName string = ''


var aciShare = 'acishare'
var qdrantShare = 'qdrantshare'

var metadataTable = 'Metadata'
var containerMetadataTable = 'ContainersMetadata'

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
   tables: [ 
    metadataTable
    containerMetadataTable
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

// Create an App Service Plan to group applications under the same payment plan and SKU
module appServicePlan './core/host/appserviceplan.bicep' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    sku: {
      name: 'EP1'
      tier: 'ElasticPremium'
      family: 'EP'
    }
    kind: 'elastic'
    reserved: false
  }
}

var appName = !empty(apiServiceName) ? apiServiceName : '${abbrs.webSitesFunctions}api-${resourceToken}'

// The application backend
module skfunc './app/sk-func.bicep' = {
  name: 'skfunc'
  scope: rg
  params: {
    name: appName
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    appServicePlanId: appServicePlan.outputs.id
    storageAccountName: storage.outputs.name
    appSettings: {
      SANDBOX_IMAGE: 'mcr.microsoft.com/dotnet/sdk:7.0'
      AzureWebJobsFeatureFlags: 'EnableHttpProxying'
      FUNCTIONS_FQDN: 'https://${appName}.azurewebsites.net'
      'GithubOptions__AppKey': githubAppKey
      'GithubOptions__AppId': githubAppId
      'GithubOptions__InstallationId': githubAppInstallationId
      'AzureOptions__SubscriptionId': subscription().subscriptionId
      'AzureOptions__Location': location
      'AzureOptions__ContainerInstancesResourceGroup': rg.name
      'AzureOptions__FilesShareName': aciShare
      'AzureOptions__FilesAccountName': storage.outputs.name
      'OpenAIOptions__ServiceType': openAIServiceType
      'OpenAIOptions__ServiceId': openAIServiceId
      'OpenAIOptions__DeploymentOrModelId': openAIDeploymentId
      'OpenAIOptions__EmbeddingDeploymentOrModelId': openAIEmbeddingId
      'OpenAIOptions__Endpoint': openAIEndpoint
      'OpenAIOptions__ApiKey': openAIKey
      'QdrantOptions__Endpoint':'https://${qdrant.outputs.fqdn}'
      'QdrantOptions__VectorSize':'1536'
    }
  }
}

// App outputs
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId


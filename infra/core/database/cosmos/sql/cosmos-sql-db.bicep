metadata description = 'Creates an Azure Cosmos DB for NoSQL account with a database.'
param accountName string
param databaseName string
param location string = resourceGroup().location
param tags object = {}

param containers array = []
param principalIds array = []

module cosmos 'cosmos-sql-account.bicep' = {
  name: 'cosmos-sql-account'
  params: {
    name: accountName
    location: location
    tags: tags
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2022-05-15' = {
  name: '${accountName}/${databaseName}'
  properties: {
    resource: { id: databaseName }
  }
  
  resource list 'containers' = [for container in containers: {
    name: container.name
    properties: {
      resource: {
        id: container.id
        partitionKey: { paths: [ container.partitionKey ] }
      }
      options: {}
    }
  }]

  dependsOn: [
    cosmos
  ]
}

module roleDefinition 'cosmos-sql-role-def.bicep' = {
  name: 'cosmos-sql-role-definition'
  params: {
    accountName: accountName
  }
  dependsOn: [
    cosmos
    database
  ]
}

// We need batchSize(1) here because sql role assignments have to be done sequentially
@batchSize(1)
module userRole 'cosmos-sql-role-assign.bicep' = [for principalId in principalIds: if (!empty(principalId)) {
  name: 'cosmos-sql-user-role-${uniqueString(principalId)}'
  params: {
    accountName: accountName
    roleDefinitionId: roleDefinition.outputs.id
    principalId: principalId
  }
  dependsOn: [
    cosmos
    database
  ]
}]

output accountId string = cosmos.outputs.id
output accountName string = cosmos.outputs.name
output connectionStringKey string = cosmos.outputs.connectionStringKey
output databaseName string = databaseName
output endpoint string = cosmos.outputs.endpoint
output roleDefinitionId string = roleDefinition.outputs.id

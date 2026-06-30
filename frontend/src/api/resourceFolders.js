import request from './index'

export function getResourceFolders(resourceType) {
  return request.get('/resource-folders/', { params: { resource_type: resourceType } })
}

export function createResourceFolder(data) {
  return request.post('/resource-folders/', data)
}

export function updateResourceFolder(id, data) {
  return request.patch(`/resource-folders/${id}/`, data)
}

export function deleteResourceFolder(id) {
  return request.delete(`/resource-folders/${id}/`)
}

export function reorderResourceFolders(order) {
  return request.post('/resource-folders/reorder/', { order })
}

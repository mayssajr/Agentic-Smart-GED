import apiClient from "./api";  

const BaseApiService = (resource) => {
  return {
    list: (config = {}) => apiClient.get(`${resource}`, config),
    get: (id, config = {}) => apiClient.get(`${resource}/${id}`, config),
    create: (payload, config = {}) =>
      apiClient.post(`${resource}`, payload, config),
    update: (id, payload, config = {}) =>
      apiClient.put(`${resource}/${id}`, payload, config),
    patch: (id, payload, config = {}) =>
      apiClient.patch(`${resource}/${id}`, payload, config),
    remove: (id, config = {}) =>
      apiClient.delete(`${resource}/${id}`, config),
    removeObj: (payload, config = {}) =>
      apiClient.delete(`${resource}`, { data: payload }, config),
  };
};
export default BaseApiService;

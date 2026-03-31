import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { nodesApi } from '../api/nodes-api'
import { useNodeCatalogStore } from '../stores/node-catalog-store'

export function useNodeCatalog() {
  const { setNodes, setLoading, setError } = useNodeCatalogStore()

  const query = useQuery({
    queryKey: ['nodes'],
    queryFn: () => nodesApi.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  })

  useEffect(() => {
    setLoading(query.isLoading)
  }, [query.isLoading, setLoading])

  useEffect(() => {
    if (query.data) setNodes(query.data.nodes)
  }, [query.data, setNodes])

  useEffect(() => {
    if (query.error) setError(String(query.error))
  }, [query.error, setError])

  return {
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  }
}

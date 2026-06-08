import { useMutation } from '@tanstack/react-query'
import { answerRetrieval, searchRetrieval } from '@/api/retrieval'

export function useRetrievalSearch() {
  return useMutation({
    mutationFn: searchRetrieval,
  })
}

export function useRetrievalAnswer() {
  return useMutation({
    mutationFn: answerRetrieval,
  })
}

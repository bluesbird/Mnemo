export type ChatSourceReference = {
  note_id: number;
  note_title: string;
  chunk_index: number;
  source_hash: string;
  score: number;
  excerpt: string;
  chunk_text?: string;
};

export type ChatQueryRequest = {
  question: string;
  history?: ChatHistoryMessage[];
  top_k?: number;
};

export type ChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatQueryResponse = {
  answer: string;
  sources: ChatSourceReference[];
};

export type IndexOperationResponse = {
  indexed_note_ids: number[];
  deleted_note_ids: number[];
  skipped_note_ids: number[];
  total_knowledge_notes: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources: ChatSourceReference[];
  isError?: boolean;
};

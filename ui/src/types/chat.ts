export type ChatSourceReference = {
  note_id: number;
  note_title: string;
  chunk_index: number;
  source_hash: string;
  score: number;
  excerpt: string;
};

export type ChatQueryRequest = {
  question: string;
  top_k?: number;
};

export type ChatQueryResponse = {
  answer: string;
  sources: ChatSourceReference[];
};

export type IndexOperationResponse = {
  indexed_note_ids: number[];
  deleted_note_ids: number[];
  skipped_note_ids: number[];
  total_ms1_notes: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources: ChatSourceReference[];
  isError?: boolean;
};

export type Note = {
  id: number;
  title: string;
  content: string;
  summary: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
};

export type NoteDraft = Pick<Note, "title" | "content">;
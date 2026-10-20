export type Note = {
  id: number;
  title: string;
  content: string;
  summary: string | null;
  createdAt: string;
  updatedAt: string;
};

export type NoteDraft = Pick<Note, "title" | "content">;
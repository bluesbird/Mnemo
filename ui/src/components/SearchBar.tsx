type SearchBarProps = {
  value: string;
  onChange: (value: string) => void;
};

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <label className="search-box">
      <span aria-hidden="true" className="search-icon">
        ⌕
      </span>
      <input
        type="search"
        placeholder="Search notes"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
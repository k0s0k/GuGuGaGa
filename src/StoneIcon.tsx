/** A rounded pebble, shared by the stone balance and collection rewards. */
export default function StoneIcon({
  size = 20,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      className={`stone-icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
      fill="none"
    >
      <g strokeLinejoin="round" strokeLinecap="round">
        <path
          d="M4 15q1-4 4-7l5-4q3-2 6 0l5 3q3 2 4 6l2 8q0 4-4 6-5 2-11 1l-7-1q-5-1-5-5Z"
          fill="#b8b3ce"
          stroke="#fff9e9"
          strokeWidth="3"
        />
        <path d="m8 8 6-4q2-1 4 0l-3 9-10 3-1 6V16q0-4 4-8Z" fill="#eee9ed" />
        <path d="m19 4 6 4 3 6 2 8-8-5-7-4Z" fill="#9c96b8" />
        <path
          d="m4 22 8 2 10-2 8-1q0 4-4 6-5 2-11 1l-7-1q-4-1-4-5Z"
          fill="#8c85a6"
        />
        <path d="m5 16 10-3 7 4v5l-10 2-8-2Z" fill="#c9c4dc" />
        <path
          d="M4 15q1-4 4-7l5-4q3-2 6 0l5 3q3 2 4 6l2 8q0 4-4 6-5 2-11 1l-7-1q-5-1-5-5Z"
          stroke="#29283f"
          strokeWidth="1.7"
        />
        <path d="m9 10 3-3" stroke="#fff9e9" strokeWidth="1.5" />
        <path
          d="M11 17v1m9-1v1m-6 3q2 2 4 0"
          stroke="#29283f"
          strokeWidth="1.7"
        />
      </g>
    </svg>
  );
}

type JourneyIconKind =
  "banner" | "code" | "knowledge" | "review" | "finish" | "complete" | "empty";

const ink = "#29283f";
const cream = "#fff9e9";
const yellow = "#ffd044";
const pink = "#ff81aa";
const lavender = "#c7b5ff";
const ice = "#9ee8f2";

/** Original flat sticker artwork. The surrounding control provides its label. */
export default function JourneyIcon({
  kind,
  current = false,
}: {
  kind: JourneyIconKind;
  current?: boolean;
}) {
  const headphones = current || kind === "banner";
  const accent =
    kind === "review"
      ? lavender
      : kind === "knowledge" || kind === "empty"
        ? ice
        : pink;
  return (
    <svg
      className="journey-icon"
      data-journey-icon={kind}
      data-current={current}
      viewBox="0 0 100 100"
      aria-hidden="true"
      focusable="false"
    >
      <g strokeLinejoin="round" strokeLinecap="round">
        <path
          className="journey-sticker-shadow"
          d="M23 13 73 10 90 29 86 72 69 90 23 87 9 67 12 32Z"
          fill={ink}
          stroke={ink}
          strokeWidth="6"
          transform="translate(1 3)"
        />
        <path
          d="M23 13 73 10 90 29 86 72 69 90 23 87 9 67 12 32Z"
          fill={yellow}
          stroke={cream}
          strokeWidth="8"
        />
        <path
          d="M23 13 73 10 90 29 86 72 69 90 23 87 9 67 12 32Z"
          fill="none"
          stroke={ink}
          strokeWidth="3.5"
        />
        <path d="m14 58 16-8 42 30-8 8-38-3Z" fill={accent} />
        <path d="m71 13 14 15-11 2-13-15Z" fill={cream} />
        <path
          d="m15 38 7-10m-8 18 5-1"
          fill="none"
          stroke={cream}
          strokeWidth="4"
        />

        <g className="journey-penguin" transform="rotate(-6 49 54)">
          <path
            d="M30 47Q16 46 16 63q8 1 16-7m34-9q15-3 17 11-9 5-17-1"
            fill={ink}
            stroke={ink}
            strokeWidth="3"
          />
          <path
            d="m33 75-9 7q8 7 20 1l-1-8m16 0 13 6q-6 8-18 3l-2-9"
            fill={yellow}
            stroke={ink}
            strokeWidth="3"
          />
          <path
            d="M26 48c-1-18 9-28 24-28s26 12 25 29l3 15c2 14-11 18-28 18S22 77 23 64Z"
            fill={ink}
            stroke={ink}
            strokeWidth="3"
          />
          <path
            d="M30 49c-1-12 6-18 13-12l7 7 7-7c8-6 15 0 14 12l4 17c1 8-11 12-25 12S25 74 26 66Z"
            fill={cream}
          />
          {headphones ? (
            <>
              <path
                d="M24 44c-1-18 10-27 26-27S78 29 76 45"
                fill="none"
                stroke={cream}
                strokeWidth="8"
              />
              <path
                d="M24 44c-1-18 10-27 26-27S78 29 76 45"
                fill="none"
                stroke={ink}
                strokeWidth="4"
              />
              <rect
                x="20"
                y="39"
                width="10"
                height="18"
                rx="4"
                fill={pink}
                stroke={ink}
                strokeWidth="3"
              />
              <rect
                x="70"
                y="39"
                width="10"
                height="18"
                rx="4"
                fill={pink}
                stroke={ink}
                strokeWidth="3"
              />
              <path d="M24 44v7m51-7v7" stroke={cream} strokeWidth="2" />
            </>
          ) : (
            <path
              d="m42 24 7-7 6 5 6-3"
              fill="none"
              stroke={ink}
              strokeWidth="3.5"
            />
          )}
          <path
            d="M35 33q8-10 20-5l10 8-8-2 2 8-8-6-4 6-4-7-8 4 3-6Z"
            fill={lavender}
            stroke={ink}
            strokeWidth="2"
          />
          {current || kind === "complete" ? (
            <g fill="none" stroke={ink} strokeWidth="3.2">
              <path d="m35 49 7 2-6 3m29-5-7 2 6 3" />
            </g>
          ) : (
            <g fill={ink}>
              <ellipse cx="39" cy="51" rx="2.6" ry="3" />
              <ellipse cx="61" cy="51" rx="2.6" ry="3" />
              <path
                d="m35 48 8 1m14 0 8-1"
                fill="none"
                stroke={ink}
                strokeWidth="2.5"
              />
            </g>
          )}
          <path
            d="m44 56 6-4 7 4-7 5Z"
            fill={yellow}
            stroke={ink}
            strokeWidth="2"
          />
          <path
            d="m31 57 6 1m26 0 6-1"
            fill="none"
            stroke={pink}
            strokeWidth="4"
          />
        </g>

        {kind === "code" && (
          <g transform="rotate(5 68 74)" stroke={ink} strokeWidth="3">
            <rect x="43" y="60" width="43" height="27" rx="5" fill={ink} />
            <path d="M47 61h34q4 0 4 4v3H44v-3q0-4 3-4" fill={ice} />
            <path
              d="m52 73 5 4-5 4m11 0h8"
              stroke={cream}
              strokeWidth="2.7"
              fill="none"
            />
            <path d="M82 64h0" stroke={pink} strokeWidth="3" />
          </g>
        )}
        {(kind === "knowledge" || kind === "empty") && (
          <g transform="rotate(7 66 74)" stroke={ink} strokeWidth="3">
            <path
              d="M44 61q11-3 20 3 11-6 22-3v25q-12-2-22 3-10-5-20-3Z"
              fill={ice}
            />
            <path
              d="M48 65q9-1 16 3 9-5 18-3v17q-9 0-18 4-8-4-16-4Z"
              fill={cream}
              stroke="none"
            />
            <path
              d="M64 65v23m-13-17 7 2m-7 5 7 2m12-7 7-2"
              fill="none"
              strokeWidth="2"
            />
            <path d="M73 63v12l4-3 4 2V62" fill={pink} strokeWidth="2" />
          </g>
        )}
        {kind === "review" && (
          <g transform="rotate(7 69 74)" stroke={ink} strokeWidth="3">
            <circle cx="69" cy="73" r="17" fill={lavender} />
            <path
              d="M57 73a12 12 0 1 0 7-11"
              fill="none"
              stroke={cream}
              strokeWidth="3"
            />
            <path
              d="m62 59-2 8 8-1"
              fill={cream}
              stroke={cream}
              strokeWidth="2"
            />
            <path d="M69 65v9l6 3" fill="none" />
          </g>
        )}
        {(kind === "banner" || kind === "finish") && (
          <g transform="rotate(9 75 49)" stroke={ink} strokeWidth="3">
            <path d="M72 31v50" fill="none" />
            <path
              d="M73 31q9-5 18-1l-2 19q-9-4-16 1Z"
              fill={kind === "finish" ? cream : pink}
            />
            {kind === "finish" ? (
              <path
                d="m74 32 7-2v8l-7 1m7-1 8-1-1 9-7-1Z"
                fill={ink}
                stroke="none"
              />
            ) : (
              <path
                d="m82 33 1 5 5 1-5 2-2 5-1-5-4-2 5-1Z"
                fill={cream}
                stroke="none"
              />
            )}
            <path d="m66 81 12 1" strokeWidth="4" />
          </g>
        )}
        {kind === "complete" && (
          <g transform="rotate(7 69 72)" stroke={ink} strokeWidth="3">
            <path d="M56 61h-5v8q0 7 10 7m19-15h6v8q0 7-10 7" fill="none" />
            <path d="M56 60h24v8q0 12-12 12T56 68Z" fill={yellow} />
            <path d="M68 80v7m-8 1h16" fill="none" strokeWidth="4" />
            <path
              d="m68 64 2 4 5 1-4 3 1 5-4-3-4 3 1-5-4-3 5-1Z"
              fill={cream}
              stroke="none"
            />
          </g>
        )}
        {current ? (
          <g transform="rotate(12 80 20)">
            <path
              d="m79 7 5 9 10 2-7 8 1 10-9-5-9 5 2-11-8-7 11-2Z"
              fill={pink}
              stroke={cream}
              strokeWidth="5"
            />
            <path
              d="m79 7 5 9 10 2-7 8 1 10-9-5-9 5 2-11-8-7 11-2Z"
              fill={pink}
              stroke={ink}
              strokeWidth="2.5"
            />
            <path d="m79 16 2 4 4 1-3 3v4l-3-2-4 2 1-4-3-3 4-1Z" fill={cream} />
          </g>
        ) : (
          <path
            d="m84 11 2 6 6 2-6 2-2 6-2-6-6-2 6-2Z"
            fill={cream}
            stroke={ink}
            strokeWidth="2"
          />
        )}
      </g>
    </svg>
  );
}

import { EditorState, Prec } from "@codemirror/state";
import { keymap } from "@codemirror/view";
import { indentUnit } from "@codemirror/language";
import {
  indentLess,
  indentMore,
  insertNewlineAndIndent,
} from "@codemirror/commands";
import {
  acceptCompletion,
  autocompletion,
  closeCompletion,
  completeAnyWord,
  moveCompletionSelection,
  startCompletion,
} from "@codemirror/autocomplete";

// Use this together with react-codemirror's indentWithTab={false} and
// basicSetup.autocompletion/completionKeymap=false to avoid competing keymaps.
export const codeEditingExtensions = [
  EditorState.tabSize.of(4),
  indentUnit.of("    "),
  EditorState.languageData.of(() => [{ autocomplete: completeAnyWord }]),
  autocompletion({ defaultKeymap: false, interactionDelay: 0 }),
  Prec.highest(
    keymap.of([
      { key: "Tab", run: (view) => acceptCompletion(view) || indentMore(view) },
      { key: "Shift-Tab", run: indentLess },
      {
        key: "Enter",
        run: (view) => {
          closeCompletion(view);
          return insertNewlineAndIndent(view);
        },
      },
      { key: "Ctrl-Space", run: startCompletion },
      { key: "ArrowDown", run: moveCompletionSelection(true) },
      { key: "ArrowUp", run: moveCompletionSelection(false) },
      { key: "PageDown", run: moveCompletionSelection(true, "page") },
      { key: "PageUp", run: moveCompletionSelection(false, "page") },
      { key: "Escape", run: closeCompletion },
    ]),
  ),
];

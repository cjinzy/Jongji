/**
 * TaskPanelComments — comment list + input for TaskDetailPanel.
 */
import { CommentRegular, PersonRegular, SendRegular } from '@fluentui/react-icons'
import type { Comment } from '../../types/task'

/** Relative time formatter */
function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

interface TaskPanelCommentsProps {
  comments: Comment[] | undefined
  value: string
  isPending: boolean
  onChange: (v: string) => void
  onSubmit: () => void
}

export function TaskPanelComments({
  comments,
  value,
  isPending,
  onChange,
  onSubmit,
}: TaskPanelCommentsProps) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-[10px] text-text-tertiary uppercase tracking-wide flex items-center gap-1">
        <CommentRegular className="w-3 h-3" />
        Comments ({comments?.length ?? 0})
      </span>

      {comments && comments.length > 0 && (
        <div className="space-y-3">
          {comments.map((comment) => (
            <div key={comment.id} className="flex gap-2.5">
              <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <PersonRegular className="w-3.5 h-3.5 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-0.5">
                  <span className="text-xs font-medium text-text-primary">
                    {comment.author?.name ?? comment.author_id}
                  </span>
                  <span className="text-[10px] text-text-tertiary">
                    {relativeTime(comment.created_at)}
                  </span>
                </div>
                <p className="text-sm text-text-secondary whitespace-pre-wrap">
                  {comment.content}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Comment input */}
      <div className="flex gap-2 mt-1">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Write a comment..."
          rows={2}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              onSubmit()
            }
          }}
          className="
            flex-1 bg-bg-tertiary border border-border rounded px-3 py-2
            text-sm text-text-primary resize-none placeholder:text-text-tertiary
            focus:outline-none focus:border-accent/60 transition-colors
          "
        />
        <button
          onClick={onSubmit}
          disabled={!value.trim() || isPending}
          className="
            w-8 h-8 self-end rounded flex items-center justify-center
            bg-accent text-white
            hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed
            transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent
          "
          aria-label="Send comment"
        >
          <SendRegular className="w-3.5 h-3.5" />
        </button>
      </div>
      <p className="text-[10px] text-text-tertiary">
        Cmd/Ctrl + Enter to submit
      </p>
    </div>
  )
}

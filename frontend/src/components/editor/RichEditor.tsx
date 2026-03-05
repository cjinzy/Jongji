import { useCallback, useRef, useState } from 'react'
import { useEditor, EditorContent, ReactRenderer } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Mention from '@tiptap/extension-mention'
import Placeholder from '@tiptap/extension-placeholder'
import Link from '@tiptap/extension-link'
import tippy from 'tippy.js'
import type { Instance as TippyInstance } from 'tippy.js'
import {
  TextBoldRegular,
  TextItalicRegular,
  TextStrikethroughRegular,
  CodeRegular,
  TextBulletListRegular,
  TextNumberListLtrRegular,
  TextQuoteRegular,
  LinkRegular,
  ImageRegular,
  DismissRegular,
  ChevronDownRegular,
} from '@fluentui/react-icons'
import MentionList from './MentionList'
import type { MentionListHandle } from './MentionList'
import { attachmentsApi } from '../../api/attachments'
import { usersApi } from '../../api/users'
import type { User } from '../../api/users'

interface RichEditorProps {
  /** Initial HTML content */
  content: string
  onChange: (content: string) => void
  placeholder?: string
  editable?: boolean
  /** Project ID used for mention user filtering */
  projectId?: string
}

type HeadingLevel = 1 | 2 | 3

/** Icon button used in the toolbar */
function ToolbarBtn({
  onClick,
  active,
  disabled,
  title,
  children,
}: {
  onClick: () => void
  active?: boolean
  disabled?: boolean
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        // Prevent editor from losing focus
        e.preventDefault()
        onClick()
      }}
      disabled={disabled}
      title={title}
      aria-label={title}
      aria-pressed={active}
      className={`
        w-7 h-7 rounded flex items-center justify-center
        transition-colors duration-100 focus-visible:outline-none
        focus-visible:ring-1 focus-visible:ring-accent
        ${active
          ? 'bg-accent/20 text-accent'
          : 'text-text-tertiary hover:text-text-primary hover:bg-bg-hover'
        }
        ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {children}
    </button>
  )
}

/** Thin vertical divider for the toolbar */
function ToolbarDivider() {
  return <div className="w-px h-4 bg-border mx-0.5" aria-hidden="true" />
}

/**
 * Tiptap rich text editor with toolbar, mention autocomplete, and image upload.
 * Renders as HTML string via onChange.
 */
export default function RichEditor({
  content,
  onChange,
  placeholder = '작업 설명을 입력하세요...',
  editable = true,
  projectId: _projectId,
}: RichEditorProps) {
  const [uploading, setUploading] = useState(false)
  const [headingMenuOpen, setHeadingMenuOpen] = useState(false)
  const imageInputRef = useRef<HTMLInputElement>(null)

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Disable default heading to configure separately — still bundled
        heading: { levels: [1, 2, 3] },
        codeBlock: { languageClassPrefix: 'language-' },
      }),
      Image.configure({ inline: false, allowBase64: false }),
      Placeholder.configure({ placeholder }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' },
      }),
      Mention.configure({
        HTMLAttributes: { class: 'mention' },
        suggestion: {
          items: async ({ query }: { query: string }): Promise<User[]> => {
            try {
              return await usersApi.search(query)
            } catch {
              return []
            }
          },
          render: () => {
            let component: ReactRenderer<MentionListHandle>
            let popup: TippyInstance[]

            return {
              onStart: (props) => {
                component = new ReactRenderer(MentionList, {
                  props,
                  editor: props.editor,
                })
                if (!props.clientRect) return
                popup = tippy('body', {
                  getReferenceClientRect: () =>
                    props.clientRect?.() ?? new DOMRect(),
                  appendTo: () => document.body,
                  content: component.element,
                  showOnCreate: true,
                  interactive: true,
                  trigger: 'manual',
                  placement: 'bottom-start',
                  theme: 'jongji',
                  arrow: false,
                  offset: [0, 6],
                })
              },
              onUpdate: (props) => {
                component.updateProps(props)
                if (!props.clientRect) return
                popup[0]?.setProps({
                  getReferenceClientRect: () =>
                    props.clientRect?.() ?? new DOMRect(),
                })
              },
              onKeyDown: (props) => {
                if (props.event.key === 'Escape') {
                  popup[0]?.hide()
                  return true
                }
                return component.ref?.onKeyDown(props.event) ?? false
              },
              onExit: () => {
                popup[0]?.destroy()
                component.destroy()
              },
            }
          },
        },
      }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  /** Handle image file upload from toolbar or paste */
  const uploadImageFile = useCallback(
    async (file: File) => {
      if (!editor) return
      setUploading(true)
      try {
        const attachment = await attachmentsApi.upload(file)
        const url = attachmentsApi.getDownloadUrl(attachment.id)
        editor.chain().focus().setImage({ src: url, alt: attachment.filename }).run()
      } catch (err) {
        console.error('Image upload failed:', err)
      } finally {
        setUploading(false)
      }
    },
    [editor],
  )

  /** Handle image paste from clipboard */
  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const items = Array.from(e.clipboardData.items)
      const imageItem = items.find((item) => item.type.startsWith('image/'))
      if (!imageItem) return
      e.preventDefault()
      const file = imageItem.getAsFile()
      if (file) uploadImageFile(file)
    },
    [uploadImageFile],
  )

  function isValidUrl(url: string): boolean {
    try {
      const parsed = new URL(url)
      return ['http:', 'https:', 'mailto:'].includes(parsed.protocol)
    } catch {
      return false
    }
  }

  function setLink() {
    if (!editor) return
    const prev = editor.getAttributes('link').href ?? ''
    const url = window.prompt('URL 입력', prev)
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      if (!isValidUrl(url)) return
      editor
        .chain()
        .focus()
        .extendMarkRange('link')
        .setLink({ href: url })
        .run()
    }
  }

  function setHeading(level: HeadingLevel) {
    editor?.chain().focus().toggleHeading({ level }).run()
    setHeadingMenuOpen(false)
  }

  function clearHeading() {
    editor?.chain().focus().setParagraph().run()
    setHeadingMenuOpen(false)
  }

  const activeHeading = ([1, 2, 3] as HeadingLevel[]).find((l) =>
    editor?.isActive('heading', { level: l }),
  )
  const headingLabel = activeHeading ? `H${activeHeading}` : 'Text'

  if (!editor) return null

  return (
    <div
      className={`
        bg-bg-tertiary border border-border rounded-lg
        focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10
        transition-all duration-150 flex flex-col
        ${!editable ? 'opacity-80 cursor-default' : ''}
      `}
    >
      {/* Toolbar */}
      {editable && (
        <div
          className="
            flex items-center gap-0.5 px-2 py-1.5
            border-b border-border flex-wrap
          "
          role="toolbar"
          aria-label="Editor toolbar"
        >
          {/* Bold */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
            title="Bold (Ctrl+B)"
          >
            <TextBoldRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Italic */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
            title="Italic (Ctrl+I)"
          >
            <TextItalicRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Strike */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleStrike().run()}
            active={editor.isActive('strike')}
            title="Strikethrough"
          >
            <TextStrikethroughRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Inline code */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleCode().run()}
            active={editor.isActive('code')}
            title="Inline Code"
          >
            <CodeRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          <ToolbarDivider />

          {/* Heading dropdown */}
          <div className="relative">
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault()
                setHeadingMenuOpen((v) => !v)
              }}
              title="Heading"
              aria-label="Heading level"
              aria-expanded={headingMenuOpen}
              aria-haspopup="menu"
              className={`
                h-7 px-1.5 rounded flex items-center gap-0.5 text-[11px] font-medium
                transition-colors duration-100 focus-visible:outline-none
                focus-visible:ring-1 focus-visible:ring-accent
                ${activeHeading
                  ? 'bg-accent/20 text-accent'
                  : 'text-text-tertiary hover:text-text-primary hover:bg-bg-hover'
                }
              `}
            >
              {headingLabel}
              <ChevronDownRegular className="w-3 h-3" />
            </button>

            {headingMenuOpen && (
              <>
                {/* Click-outside overlay */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setHeadingMenuOpen(false)}
                />
                <div
                  className="
                    absolute left-0 top-full mt-1 z-20
                    bg-bg-secondary border border-border rounded-lg shadow-lg
                    py-1 min-w-[100px]
                  "
                  role="menu"
                >
                  <button
                    type="button"
                    role="menuitem"
                    onMouseDown={(e) => { e.preventDefault(); clearHeading() }}
                    className="w-full text-left px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
                  >
                    Text
                  </button>
                  {([1, 2, 3] as HeadingLevel[]).map((l) => (
                    <button
                      key={l}
                      type="button"
                      role="menuitem"
                      onMouseDown={(e) => { e.preventDefault(); setHeading(l) }}
                      className={`
                        w-full text-left px-3 py-1.5 text-xs transition-colors
                        hover:bg-bg-hover
                        ${activeHeading === l ? 'text-accent font-medium' : 'text-text-secondary hover:text-text-primary'}
                      `}
                    >
                      Heading {l}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          <ToolbarDivider />

          {/* Bullet list */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
            title="Bullet List"
          >
            <TextBulletListRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Ordered list */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive('orderedList')}
            title="Ordered List"
          >
            <TextNumberListLtrRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Blockquote */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive('blockquote')}
            title="Blockquote"
          >
            <TextQuoteRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Code block */}
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            active={editor.isActive('codeBlock')}
            title="Code Block"
          >
            <span className="text-[10px] font-mono font-bold leading-none">{'</>'}</span>
          </ToolbarBtn>

          <ToolbarDivider />

          {/* Link */}
          <ToolbarBtn
            onClick={setLink}
            active={editor.isActive('link')}
            title="Insert Link"
          >
            <LinkRegular className="w-3.5 h-3.5" />
          </ToolbarBtn>

          {/* Image upload */}
          <ToolbarBtn
            onClick={() => imageInputRef.current?.click()}
            disabled={uploading}
            title={uploading ? 'Uploading...' : 'Insert Image'}
          >
            {uploading ? (
              <span className="w-3.5 h-3.5 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
            ) : (
              <ImageRegular className="w-3.5 h-3.5" />
            )}
          </ToolbarBtn>

          {/* Clear formatting shortcut indicator */}
          {(editor.isActive('link') || editor.isActive('bold') || editor.isActive('italic')) && (
            <>
              <ToolbarDivider />
              <ToolbarBtn
                onClick={() =>
                  editor.chain().focus().clearNodes().unsetAllMarks().run()
                }
                title="Clear formatting"
              >
                <DismissRegular className="w-3.5 h-3.5" />
              </ToolbarBtn>
            </>
          )}
        </div>
      )}

      {/* Hidden image file input */}
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        aria-hidden="true"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) uploadImageFile(file)
          e.target.value = ''
        }}
      />

      {/* Editor content area */}
      <div onPaste={handlePaste} className="relative">
        <EditorContent
          editor={editor}
          className="rich-editor-content"
        />
        {uploading && (
          <div className="
            absolute bottom-2 right-3
            text-[10px] text-text-tertiary flex items-center gap-1.5
          ">
            <span className="w-3 h-3 border border-accent/40 border-t-accent rounded-full animate-spin" />
            업로드 중...
          </div>
        )}
      </div>
    </div>
  )
}

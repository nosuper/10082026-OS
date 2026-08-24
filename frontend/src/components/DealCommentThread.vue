<!--
  The deal's comment thread.

  Lives in its own component for two reasons. The card dialog is already
  long enough that the founder called it "okay, refine later", and the
  editor this thread needs (mentions, pasted images) is a large chunk of
  JavaScript that no other screen wants - the dialog loads it lazily, so
  the deal board still opens on what it always cost.

  Posting, editing and deleting each go straight to the server, the way
  comments always have here: they are not part of the dialog's Save.
-->
<template>
  <!-- `comment-thread` is a handle, not a style: the dialog's own Save
       and Cancel share their labels with the ones an edited comment
       shows, and the browser tests need to tell them apart. -->
  <div class="comment-thread">
    <div class="mb-2 text-xs font-medium text-gray-700">Comments</div>

    <div class="space-y-2">
      <div
        v-for="comment in comments.data || []"
        :key="comment.name"
        class="rounded-md bg-gray-50 px-3 py-2"
      >
        <div class="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <span class="font-medium text-gray-700">
            {{ comment.comment_by || comment.comment_email }}
          </span>
          <span class="tabular-nums">{{ comment.creation?.slice(0, 16) }}</span>
          <span v-if="comment.edited" class="italic">edited</span>
          <template v-if="comment.mine && editing !== comment.name">
            <button
              class="ml-auto rounded px-1.5 py-0.5 hover:bg-gray-200 hover:text-gray-800"
              @click="startEditing(comment)"
            >
              Edit
            </button>
            <!-- Two taps rather than a browser confirm: a modal dialog
                 inside a modal dialog is the one thing worse than a
                 mis-tap. -->
            <button
              v-if="confirming !== comment.name"
              class="rounded px-1.5 py-0.5 hover:bg-gray-200 hover:text-gray-800"
              @click="confirming = comment.name"
            >
              Delete
            </button>
            <template v-else>
              <button
                class="rounded px-1.5 py-0.5 font-medium text-red-700 hover:bg-red-50"
                @click="remove(comment)"
              >
                Delete for good
              </button>
              <button
                class="rounded px-1.5 py-0.5 hover:bg-gray-200"
                @click="confirming = null"
              >
                Keep
              </button>
            </template>
          </template>
        </div>

        <div v-if="editing === comment.name" class="mt-1.5">
          <div class="rounded-md border border-gray-300 bg-white">
            <TextEditor
              :content="draft"
              :mentions="mentionable"
              :upload-args="uploadArgs"
              editor-class="prose-sm max-w-none px-3 py-2 focus:outline-none"
              placeholder="Write a comment"
              @change="draft = $event"
            />
          </div>
          <div class="mt-1.5 flex gap-1.5">
            <Button
              variant="solid"
              :loading="editComment.loading"
              @click="saveEdit(comment)"
            >
              Save
            </Button>
            <Button @click="cancelEditing">Cancel</Button>
          </div>
        </div>

        <!-- Server-sanitised HTML (auraos.api._clean_comment): what makes
             a pasted screenshot and an @name render as they were typed. -->
        <div
          v-else
          class="comment-body prose prose-sm mt-0.5 max-w-none text-sm text-gray-800"
          v-html="comment.content"
        ></div>
      </div>
    </div>

    <div class="mt-2">
      <div class="rounded-md border border-gray-300 bg-white">
        <TextEditor
          :key="composerKey"
          :content="newComment"
          :mentions="mentionable"
          :upload-args="uploadArgs"
          editor-class="prose-sm max-w-none px-3 py-2 focus:outline-none"
          placeholder="Write a comment"
          @change="newComment = $event"
        />
      </div>
      <div class="mt-1.5 flex items-center gap-2">
        <span class="text-xs text-gray-400">
          Type @ to notify · paste an image to put it in the comment
        </span>
        <Button
          class="ml-auto"
          variant="subtle"
          :loading="addComment.loading"
          @click="post"
        >
          Comment
        </Button>
      </div>
    </div>

    <ErrorMessage class="mt-1" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { Button, ErrorMessage, TextEditor, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { currentUser } from "../utils/user"

const props = defineProps({
  // The deal whose thread this is - always an existing one.
  deal: { type: String, required: true },
  // [{name, full_name}] from auraos.api.operating_users
  owners: { type: Array, default: () => [] },
})

const error = ref("")
const editing = ref(null)
const confirming = ref(null)
const draft = ref("")
const newComment = ref("")
// Remounts the composer after a post: clearing `content` alone leaves
// the editor's own history (and an undo back to the sent comment).
const composerKey = ref(0)

// Naming yourself notifies nobody, so don't offer it.
const me = currentUser()
const mentionable = computed(() =>
  props.owners
    .filter((user) => user.name !== me)
    .map((user) => ({ id: user.name, label: user.full_name || user.name }))
)

// Comment images are ordinary deal attachments: uploaded private and
// readable by exactly the seats that may read the deal, which is what
// makes a pasted screenshot show for both of them and nobody else.
const uploadArgs = computed(() => ({
  doctype: "Deal",
  docname: props.deal,
  private: true,
}))

const comments = createResource({ url: "auraos.api.deal_comments" })

function reload() {
  error.value = ""
  editing.value = null
  confirming.value = null
  comments.fetch({ deal: props.deal })
}

watch(() => props.deal, reload, { immediate: true })

function onError(err) {
  error.value = frappeErrorMessage(err)
}

const addComment = createResource({
  url: "auraos.api.add_deal_comment",
  onSuccess() {
    newComment.value = ""
    composerKey.value += 1
    reload()
  },
  onError,
})

const editComment = createResource({
  url: "auraos.api.edit_deal_comment",
  onSuccess: reload,
  onError,
})

const deleteComment = createResource({
  url: "auraos.api.delete_deal_comment",
  onSuccess: reload,
  onError,
})

// An empty editor still sends "<p></p>", and a comment that is nothing
// but a pasted picture has no text at all - the same rule the server
// holds (auraos/lib/comments.py), so the button and the endpoint agree.
function isBlank(html) {
  if (/<img\b/i.test(html || "")) return false
  const el = document.createElement("div")
  el.innerHTML = html || ""
  return !el.textContent.replace(/\u00a0/g, " ").trim()
}

function post() {
  if (isBlank(newComment.value)) return
  error.value = ""
  addComment.submit({ deal: props.deal, content: newComment.value })
}

function startEditing(comment) {
  confirming.value = null
  editing.value = comment.name
  draft.value = comment.content
}

function cancelEditing() {
  editing.value = null
  draft.value = ""
}

function saveEdit(comment) {
  if (isBlank(draft.value)) return
  error.value = ""
  editComment.submit({ comment: comment.name, content: draft.value })
}

function remove(comment) {
  error.value = ""
  deleteComment.submit({ comment: comment.name })
}

defineExpose({ reload })
</script>

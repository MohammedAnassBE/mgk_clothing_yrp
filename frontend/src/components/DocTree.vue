<template>
  <div class="doc-tree">
    <div v-if="loading" class="dt-state">
      <i class="pi pi-spin pi-spinner" /> Loading tree…
    </div>
    <div v-else-if="error" class="dt-state dt-error">
      <i class="pi pi-exclamation-triangle" /> {{ error }}
    </div>
    <div v-else-if="!roots.length" class="dt-state">
      <i class="pi pi-inbox" /> No records
    </div>
    <div v-else class="dt-panel">
      <DocTreeNode v-for="n in roots" :key="n.name" :node="n" />
    </div>
  </div>
</template>

<script setup>
import { ref, provide, onMounted } from "vue"
import { useRouter } from "vue-router"
import { getTreeChildren } from "@/api/client"
import DocTreeNode from "@/components/DocTreeNode.vue"

const props = defineProps({
  doctype: { type: String, required: true },
  docRoute: { type: String, required: true },
})

const router = useRouter()
const roots = ref([])
const loading = ref(true)
const error = ref("")

function mapNodes(list) {
  return (list || []).map((c) => ({
    name: c.value,
    title: c.title || c.value,
    expandable: !!c.expandable,
    expanded: false,
    childLoading: false,
    error: false,
    children: null,
  }))
}

// Lazy expand: fetch one level the first time a group opens, then just toggle.
async function loadChildren(node) {
  if (!node.expandable) return
  if (node.children === null) {
    node.childLoading = true
    node.error = false
    try {
      node.children = mapNodes(await getTreeChildren(props.doctype, node.name))
    } catch (e) {
      // Leave children=null so a re-click retries instead of caching a dead empty.
      node.error = true
      node.childLoading = false
      return
    }
    node.childLoading = false
  }
  node.expanded = !node.expanded
}

function openNode(node) {
  router.push(`/${props.docRoute}/${encodeURIComponent(node.name)}`)
}

provide("docTree", { loadChildren, openNode })

onMounted(async () => {
  try {
    roots.value = mapNodes(await getTreeChildren(props.doctype, ""))
  } catch (e) {
    error.value = (e && e.message) || "Failed to load tree"
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.doc-tree {
  margin-top: 4px;
}
.dt-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 10px 10px 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}
.dt-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 38px 16px;
  color: #64748b;
  font-size: 14px;
}
.dt-error {
  color: #b91c1c;
}
</style>

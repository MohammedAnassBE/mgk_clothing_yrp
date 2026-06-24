<template>
  <div class="dtn">
    <div
      class="dtn-row"
      :class="{ 'is-grp': node.expandable, 'is-leaf': !node.expandable }"
      @click="onOpen"
    >
      <span
        class="dtn-chev"
        :class="{ hidden: !node.expandable, open: node.expanded }"
        @click.stop="onToggle"
      >
        <i :class="node.childLoading ? 'pi pi-spin pi-spinner' : 'pi pi-chevron-right'" />
      </span>
      <span class="dtn-ico"><i :class="node.expandable ? 'pi pi-folder' : 'pi pi-box'" /></span>
      <span class="dtn-label">{{ node.title }}</span>
      <span class="dtn-pad" />
      <span class="dtn-badge" :class="node.expandable ? 'grp' : 'itm'">
        {{ node.expandable ? "GROUP" : "ITEM" }}
      </span>
      <i
        v-if="node.error"
        class="pi pi-exclamation-circle dtn-err"
        title="Couldn't load — click the chevron to retry"
      />
    </div>
    <div v-if="node.expandable && node.expanded && node.children" class="dtn-children">
      <p v-if="!node.children.length" class="dtn-empty">No items</p>
      <DocTreeNode v-for="child in node.children" :key="child.name" :node="child" />
    </div>
  </div>
</template>

<script setup>
import { inject } from "vue"

defineOptions({ name: "DocTreeNode" })

const props = defineProps({
  node: { type: Object, required: true },
})

const { loadChildren, openNode } = inject("docTree")

function onToggle() {
  loadChildren(props.node)
}
function onOpen() {
  openNode(props.node)
}
</script>

<style scoped>
.dtn-children {
  margin-left: 15px;
}
.dtn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  padding: 11px 14px;
  margin: 6px 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.14s, border-color 0.14s, transform 0.04s;
}
.dtn-row:hover {
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  border-color: #cbd5e1;
}
.dtn-row:active {
  transform: translateY(1px);
}
.dtn-row.is-grp {
  border-left: 3px solid #10b981;
}
.dtn-chev {
  flex: none;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
  transition: transform 0.16s;
}
.dtn-chev.open {
  transform: rotate(90deg);
}
.dtn-chev.hidden {
  visibility: hidden;
}
.dtn-ico {
  flex: none;
  display: grid;
  place-items: center;
  font-size: 16px;
}
.dtn-row.is-grp .dtn-ico {
  color: #059669;
}
.dtn-row.is-leaf .dtn-ico {
  color: #94a3b8;
}
.dtn-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dtn-row.is-leaf .dtn-label {
  font-weight: 500;
  color: #475569;
}
.dtn-pad {
  flex: 1;
}
.dtn-badge {
  flex: none;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.4px;
  border-radius: 6px;
  padding: 3px 9px;
}
.dtn-badge.grp {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #d1fae5;
}
.dtn-badge.itm {
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.dtn-err {
  flex: none;
  color: #dc2626;
  font-size: 14px;
}
.dtn-empty {
  margin: 4px 0 4px 30px;
  font-size: 12.5px;
  font-style: italic;
  color: #94a3b8;
}
</style>

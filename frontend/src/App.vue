<template>
	<Toast position="bottom-right" />
	<ConfirmDialog />
	<router-view />
</template>

<script setup>
import Toast from "primevue/toast"
import ConfirmDialog from "primevue/confirmdialog"
</script>

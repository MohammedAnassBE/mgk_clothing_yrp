import { createApp } from "vue"
import PrimeVue from "primevue/config"
import ToastService from "primevue/toastservice"
import ConfirmationService from "primevue/confirmationservice"

import router from "./router"
import App from "./App.vue"
import MgkPreset from "./theme"

import "primeicons/primeicons.css"
import "./assets/styles/global.css"

const app = createApp(App)

app.use(router)
app.use(PrimeVue, {
	theme: {
		preset: MgkPreset,
		options: {
			// We ship light-only for the first slice; scope dark under `.dark`
			// so Aura never auto-applies the OS dark scheme.
			darkModeSelector: ".dark",
		},
	},
})
app.use(ToastService)
app.use(ConfirmationService)

app.mount("#app")

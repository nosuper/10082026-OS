import { createApp } from "vue"
import { setConfig, frappeRequest, resourcesPlugin } from "frappe-ui"
import App from "./App.vue"
import { router } from "./router"
import "./index.css"

setConfig("resourceFetcher", frappeRequest)

const app = createApp(App)
app.use(resourcesPlugin)
app.use(router)
app.mount("#aura-frontend-root")

const userFields = [
	"email", "first_name", "middle_name", "last_name", "username",
	"user_type", "send_welcome_email", "language", "time_zone", "module_profile",
	"mobile_no", "phone", "location", "gender", "birth_date",
]

export default {
	allowFormFields: userFields,
	hideChildTables: ["user_emails", "social_logins", "active_sessions", "roles", "role_profiles", "block_modules", "defaults"],
	detailGroups: [
		{ label: "User identity", fields: ["full_name", "email", "username", "enabled", "user_type"] },
		{ label: "Contact", fields: ["mobile_no", "phone", "location"] },
		{ label: "Access defaults", fields: ["language", "time_zone", "module_profile", "last_active"] },
	],
	formOrder: userFields,
	formGroups: [
		{ label: "User identity", fields: ["enabled", "email", "first_name", "middle_name", "last_name", "username", "user_type", "send_welcome_email"] },
		{ label: "Access defaults", fields: ["language", "time_zone", "module_profile"] },
		{ label: "Contact details", fields: ["mobile_no", "phone", "location", "gender", "birth_date"] },
	],
	help: {
		email: "This becomes the User ID used to sign in.",
		send_welcome_email: "Send the new user a link to set their password.",
		module_profile: "Optionally limit which Desk modules this user can open.",
	},
}

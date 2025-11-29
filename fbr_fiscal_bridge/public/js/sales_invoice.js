frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm){
        if(frm.doc.docstatus == 1){
        if(is_null(frm.doc.fbr_invoice_no)){
            frm.add_custom_button(__("Update FBR Invoice"), ()=>{
                console.log("hello_world")
                frappe.call({
                    method: "fbr_invoice.events.sales_invoice.send_pos_invoice_fbr",
                    args:{
                        doc: frm.doc
                    },
                    async: false,
                    callback: function(e){
                        frm.reload_doc();

                    }
                })
            })
        }
    }},
    onload: function(frm){
        if(frm.is_new() == 1){
            frappe.new_doc = true
        }
    },

})
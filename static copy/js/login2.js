const roleSelect = document.getElementById("roleSelect");

roleSelect.addEventListener("change", function(){

let role = roleSelect.value;

if(role === "admin"){
alert("Admin login selected");
}
else{
alert("Client login selected");
}

});

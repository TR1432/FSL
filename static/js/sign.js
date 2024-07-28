function toggle_pass(x){
    var x = document.getElementById(x);
  if (x.type === "password") {
    x.type = "text";
  } else {
    x.type = "password";
  }
}

$(document).ready(function() {
    let budgetRemaining = parseFloat($('#budget-remaining').text());
    let selectedPlayer = null;

    function countPlayersFromTeam(teamName) {
        let count = 0;
        $('.player').each(function() {
            if ($(this).data('team') === teamName) {
                count++;
            }
        });
        console.log(count);
        console.log(teamName)
        return count;
    }

    function attachPlayerClickListeners() {
        $('.player').off('click').click(function() {
            if (selectedPlayer) {
                selectedPlayer.removeClass('selected');
            }
            selectedPlayer = $(this);
            selectedPlayer.addClass('selected');
        });
    }

    function attachAvailablePlayerClickListeners() {
        $('.available-player').off('click').click(function() {
            if (!selectedPlayer) {
                alert('Please select a player from your team first');
                return;
            }

            const newPlayerRow = $(this);
            const newPlayerId = newPlayerRow.data('id');
            const newPlayerPrice = parseFloat(newPlayerRow.data('price'));
            const newPosition = newPlayerRow.data('position');
            const newTeam = newPlayerRow.data('team');

            const playerId = selectedPlayer.data('id');
            const playerPrice = parseFloat(selectedPlayer.data('price'));
            const position = selectedPlayer.data('position');
            const teamName = selectedPlayer.data('team');

            if (countPlayersFromTeam(newTeam) >= 3) {
                alert(`You cannot pick more than 3 players from the same team (${newTeam}).`);
                return;
            }

            let isAlreadyInTeam = false;
            $('.player').each(function() {
                if ($(this).data('id') === newPlayerId) {
                    isAlreadyInTeam = true;
                    return false; 
                }
            });

            if (isAlreadyInTeam) {
                alert('This player is already in your team');
                return;
            }

            if (position === newPosition) {
                if (newPlayerPrice <= (budgetRemaining + playerPrice)) {
                    budgetRemaining = budgetRemaining + playerPrice - newPlayerPrice;
                    $('#budget-remaining').text(budgetRemaining.toFixed(2));

                    selectedPlayer.data('id', newPlayerId);
                    selectedPlayer.data('price', newPlayerPrice);
                    selectedPlayer.data('team', newTeam);
                    selectedPlayer.find('div').text(newPlayerRow.find('td:nth-child(1)').text());

                    selectedPlayer.removeClass('selected'); 
                    selectedPlayer = null;
                } else {
                    alert('Not enough budget remaining for this transfer');
                }
            } else {
                alert('Cannot swap players from different positions');
            }
        });
    }

    $('#submit').click(function() {
        const teamPlayers = [];
    
        $('.player').each(function() {
            teamPlayers.push($(this).data('id'));
        });
    
        $.ajax({
            url: '/maketransfer',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ players: teamPlayers }),
            success: function(response) {
                alert(response.message);
                window.location.href = "/transfers";
            },
            error: function(xhr) {
                let errorMessage = 'Error making transfers, please refresh the page';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMessage = xhr.responseJSON.error;
                }
                alert(errorMessage);
            }
        });
    }); 

    function attachInputListeners() {
        $("input, select").off('input').on("input", async function() {
            let response = await fetch('/filter?argument=' + $(this).val());
            let filteredplayers = await response.text();
            document.querySelector("tbody.text-white").innerHTML = filteredplayers;
            attachAvailablePlayerClickListeners();
        });
    }

    attachPlayerClickListeners();
    attachAvailablePlayerClickListeners();
    attachInputListeners();
});

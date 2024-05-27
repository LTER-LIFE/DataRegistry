$(document).ready(function(){
    $( function() {
        function split( val ) {
          return val.split( /,\s*/ );
        }
        function extractLast( term ) {
          return split( term ).pop();
        }

    $( "#keyword_div input[placeholder]" )
        // don't navigate away from the field on tab when selecting an item
        .on( "keydown", function( event ) {
            if ( event.keyCode === $.ui.keyCode.TAB &&
                $( this ).autocomplete( "instance" ).menu.active ) {
            event.preventDefault();
        }
        })
        .autocomplete({
            source: function( request, response ) {
                $.ajax( {
                    url: keywords_url,
                    dataType: "json",
                    headers: { "Authorization":  header},
                    data: {
                        term: request.term
                    },
                success: function( data ) {
                    response( data );
                    }
                });
            },
            search: function() {
                // custom minLength
                var term = extractLast( this.value );
                if ( term.length < 2 ) {
                    return false;
                }
            },
            select: function( event, ui ) {
                var terms = split( this.value );
                // remove the current input
                terms.pop();

                // add the selected item
                terms.push( ui.item.keyword_name );
                // add placeholder to get the comma-and-space at the end
                terms.push( "" );
                this.value = terms.join( ", " );
                return false;
                }
        })
        .autocomplete( "instance" )._renderItem = function( ul, item ) {
            return $( "<li>" )
                .append( "<div>" + item.keyword_name + "</div>" )
                .appendTo( ul );
        }


    $( "#project_name_div input[placeholder]" )
    // don't navigate away from the field on tab when selecting an item
    .on( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).autocomplete( "instance" ).menu.active ) {
        event.preventDefault();
    }
    })
    .autocomplete({
        source: function( request, response ) {
            $.ajax( {
                url: projects_url,
                dataType: "json",
                headers: { "Authorization":  header},
                data: {
                    term: request.term
                },
            success: function( data ) {
                response( data );
                }
            });
        },
        search: function() {
            // custom minLength
            var term = extractLast( this.value );
            if ( term.length < 2 ) {
                return false;
            }
        },
        select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();

            // add the selected item
            terms.push( ui.item.project_name );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            $( "#group_leader_div input[placeholder]" ).val(ui.item.project_owner.user_email)
            $( "#group_leader_div input[placeholder]" ).focus()
            $( "#project_description_div textarea[name=project_description]" ).val(ui.item.project_description)
            $( "#project_description_div textarea[name=project_description]" ).focus()
            return false;
            }
    })
    .autocomplete( "instance" )._renderItem = function( ul, item ) {
        return $( "<li>" )
            .append( "<div>" + item.project_name + "</div>" )
            .appendTo( ul );
    }

    $( "#contact_div input[placeholder]" )
    // don't navigate away from the field on tab when selecting an item
    .on( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).autocomplete( "instance" ).menu.active ) {
        event.preventDefault();
    }
    })
    .autocomplete({
        source: function( request, response ) {
            $.ajax( {
                url: users_url,
                dataType: "json",
                headers: { "Authorization":  header},
                data: {
                    term: request.term
                },
            success: function( data ) {
                response( data );
                }
            });
        },
        search: function() {
            // custom minLength
            var term = extractLast( this.value );
            if ( term.length < 2 ) {
                return false;
            }
        },
        select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();

            // add the selected item
            terms.push( ui.item.user_email );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
            }
    })
    .autocomplete( "instance" )._renderItem = function( ul, item ) {
        return $( "<li>" )
            .append( "<div>" + item.user_email + "</div>" )
            .appendTo( ul );
    }

    $( "#group_leader_div input[placeholder]" )
    // don't navigate away from the field on tab when selecting an item
    .on( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).autocomplete( "instance" ).menu.active ) {
        event.preventDefault();
    }
    })
    .autocomplete({
        source: function( request, response ) {
            $.ajax( {
                url: users_url,
                headers: { "Authorization":  header},
                dataType: "json",
                data: {
                    term: request.term
                },
            success: function( data ) {
                response( data );
                }
            });
        },
        search: function() {
            // custom minLength
            var term = extractLast( this.value );
            if ( term.length < 2 ) {
                return false;
            }
        },
        select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();

            // add the selected item
            terms.push( ui.item.user_email );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
            }
    })
    .autocomplete( "instance" )._renderItem = function( ul, item ) {
        return $( "<li>" )
            .append( "<div>" + item.user_email + "</div>" )
            .appendTo( ul );
    }

$( "#contributors_div input[placeholder]" )
    // don't navigate away from the field on tab when selecting an item
    .on( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).autocomplete( "instance" ).menu.active ) {
        event.preventDefault();
    }
    })
    .autocomplete({
        source: function( request, response ) {
            $.ajax( {
                url: users_url,
                dataType: "json",
                headers: { "Authorization":  header},
                data: {
                    term: request.term
                },
            success: function( data ) {
                response( data );
                }
            });
        },
        search: function() {
            // custom minLength
            var term = extractLast( this.value );
            if ( term.length < 2 ) {
                return false;
            }
        },
        select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();

            // add the selected item
            terms.push( ui.item.user_email );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
            }
    })
    .autocomplete( "instance" )._renderItem = function( ul, item ) {
        return $( "<li>" )
            .append( "<div>" + item.user_email + "</div>" )
            .appendTo( ul );
    }
$( "#research_group_div input[placeholder]" )
    // don't navigate away from the field on tab when selecting an item
    .on( "keydown", function( event ) {
        if ( event.keyCode === $.ui.keyCode.TAB &&
            $( this ).autocomplete( "instance" ).menu.active ) {
        event.preventDefault();
    }
    })
    .autocomplete({
        source: function( request, response ) {
            $.ajax( {
                url: research_group_url,
                dataType: "json",
                headers: { "Authorization":  header},
                data: {
                    term: request.term
                },
            success: function( data ) {
                response( data );
                }
            });
        },
        search: function() {
            // custom minLength
            var term = extractLast( this.value );
            if ( term.length < 2 ) {
                return false;
            }
        },
        select: function( event, ui ) {
            var terms = split( this.value );
            // remove the current input
            terms.pop();

            // add the selected item
            terms.push( ui.item.research_group );
            // add placeholder to get the comma-and-space at the end
            terms.push( "" );
            this.value = terms.join( ", " );
            return false;
            }
    })
    .autocomplete( "instance" )._renderItem = function( ul, item ) {
        return $( "<li>" )
            .append( "<div>" + item.research_group + "</div>" )
            .appendTo( ul );
    }
    });

});

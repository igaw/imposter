widgets = service_entry_ui.py agent_ui.py manager_ui.py technology_entry_ui.py service_pane_ui.py

all: $(widgets)

$(widgets): %_ui.py: %.ui
	pyuic4 -o $@ $<

clean:
	rm -f *_ui.py
	rm -f *.pyc




document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-mask]').forEach(function (el) {
        var maskType = el.getAttribute('data-mask');
        var maskOptions;

        switch (maskType) {
            case 'telefone':
                maskOptions = { mask: '(00) 00000-0000' };
                break;
            case 'cpf':
                maskOptions = { mask: '000.000.000-00' };
                break;
            case 'cnpj':
                maskOptions = { mask: '00.000.000/0000-00' };
                break;
            case 'documento':
                maskOptions = {
                    mask: [
                        { mask: '000.000.000-00', maxLength: 11 },
                        { mask: '00.000.000/0000-00', maxLength: 14 }
                    ],
                    dispatch: function (appended, dynamicMasked) {
                        var number = (dynamicMasked.value + appended).replace(/\D/g, '');
                        return dynamicMasked.compiledMasks.find(function (m) {
                            return number.length <= m.maxLength;
                        });
                    }
                };
                break;
            case 'cep':
                maskOptions = { mask: '00000-000' };
                break;
        }

        if (maskOptions) {
            IMask(el, maskOptions);
        }
    });
});
